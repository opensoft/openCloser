"""Typer CLI — openCloser operator surface.

Slice 1 subcommands:
- `init-state`           — create state DB and apply schema (idempotent)
- `load-queue-item`      — INSERT a queue item from a JSON fixture
- `run-one`              — process exactly one queue record end-to-end (mock CRM)

Slice 2 subcommands (contracts/cli-slice2.md):
- `discover-crm`         — one-time Dataverse metadata discovery (FR-001/FR-004)
- `run-crm`              — process exactly one Dataverse queue item (FR-031/FR-032)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from opencloser.core.clock import SystemClock
from opencloser.core.config import (
    Slice2ConfigError,
    load_config,
    load_dataverse_secrets,
    load_slice2_config,
)
from opencloser.core.orchestrator import QueueItemNotFound, process_one_queue_item
from opencloser.crm.dataverse.auth import DataverseTokenProvider
from opencloser.crm.dataverse.client import DataverseClient
from opencloser.crm.dataverse.errors import DataverseError
from opencloser.crm.dataverse.mapping import MappingError, load_mapping
from opencloser.crm.dataverse.metadata import MetadataError, discover
from opencloser.crm.dataverse.queue_loader import ExplicitId, NextReady, QueueSelector
from opencloser.crm.mock import MockWriteBackAdapter
from opencloser.eligibility.evaluator import BuiltinEligibilityEvaluator
from opencloser.models import QueueItem
from opencloser.persona.alf_appointment_setter import ALFAppointmentSetterPersona
from opencloser.persona.base import ConversationFixture, ConversationTurn
from opencloser.slice2.runner import run_one_crm_item
from opencloser.state import store
from opencloser.transport.mock import FixtureDrivenTransport

app = typer.Typer(
    name="opencloser",
    help="openCloser — CRM-first AI communication CLI.",
    no_args_is_help=True,
)


_DEFAULT_CONFIG_PATH = Path("config/slice1.toml")
_DEFAULT_SLICE2_CONFIG = Path("config/slice2.toml")

# Exit-status mapping per contracts/cli-slice2.md.
_EXIT_CODE: dict[str, int] = {
    "completed": 0,
    "no-callable-item": 0,
    "blocked": 1,
    "resume_needed": 2,
    "failed": 2,
}

# Dataverse GUIDs are 8-4-4-4-12 lowercase/uppercase hex with hyphens. The CLI
# validates `--queue-item-id` against this shape before it lands in any OData
# `$filter` or record URL — that closes a filter-injection vector for
# operator-supplied input and surfaces a typo as a clean error rather than a
# 404 from the queue loader.
_GUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


@app.command(name="init-state")
def init_state(
    config_path: Annotated[
        Path, typer.Option("--config", help="Path to slice1.toml")
    ] = _DEFAULT_CONFIG_PATH,
) -> None:
    """Create the SQLite state DB and apply the schema (idempotent)."""
    config = load_config(config_path)
    clock = SystemClock()
    conn = store.connect(config.state.db)
    try:
        store.init_schema(conn, now_utc_ms=clock.now_utc_ms())
        typer.echo(f"state_db:    {config.state.db}")
        typer.echo("schema:      slice1-v1 applied")
    finally:
        conn.close()


@app.command(name="load-queue-item")
def load_queue_item(
    file: Annotated[Path, typer.Option("--file", help="Path to a queue-item JSON fixture")],
    config_path: Annotated[
        Path, typer.Option("--config", help="Path to slice1.toml")
    ] = _DEFAULT_CONFIG_PATH,
) -> None:
    """INSERT a queue item from a JSON fixture into local state."""
    config = load_config(config_path)
    raw = json.loads(file.read_text(encoding="utf-8"))
    item = QueueItem.model_validate(raw)
    conn = store.connect(config.state.db)
    try:
        with store.transaction(conn):
            store.insert_queue_item(conn, item)
        typer.echo(f"loaded:      {item.queue_item_id}")
    finally:
        conn.close()


@app.command(name="run-one")
def run_one(
    queue_item_id: Annotated[
        str, typer.Option("--queue-item-id", help="The queue-item ID to process")
    ],
    conversation_fixture: Annotated[
        Path | None,
        typer.Option(
            "--conversation-fixture",
            help="Path to a scripted conversation JSON (required when eligibility allows the call)",
        ),
    ] = None,
    transport_fixture: Annotated[
        Path | None,
        typer.Option(
            "--transport-fixture",
            help="Path to a transport-events JSON (required when eligibility allows the call)",
        ),
    ] = None,
    config_path: Annotated[
        Path, typer.Option("--config", help="Path to slice1.toml")
    ] = _DEFAULT_CONFIG_PATH,
) -> None:
    """Process exactly one queue record end-to-end (FR-025)."""
    config = load_config(config_path)
    persona = ALFAppointmentSetterPersona()
    if persona.version != config.persona.version:
        typer.echo(
            f"error:       config persona.version {config.persona.version!r} does not match "
            f"the available persona {persona.version!r}",
            err=True,
        )
        raise typer.Exit(code=2)
    conn = store.connect(config.state.db)
    try:
        # Locate transport fixtures dir + fixture id.
        if transport_fixture is not None:
            transport_dir = transport_fixture.parent
            transport_fixture_id = transport_fixture.stem
        else:
            transport_dir = Path("tests/fixtures/transport_events")
            transport_fixture_id = None

        try:
            # Load conversation fixture if provided.
            conversation = (
                _load_conversation_fixture(conversation_fixture) if conversation_fixture else None
            )
            report = process_one_queue_item(
                queue_item_id,
                conn=conn,
                config=config,
                eligibility=BuiltinEligibilityEvaluator(),
                transport=FixtureDrivenTransport(transport_dir),
                persona=persona,
                crm=MockWriteBackAdapter(conn),
                conversation_fixture=conversation,
                transport_fixture_id=transport_fixture_id,
            )
        except QueueItemNotFound as exc:
            typer.echo(f"error:       queue_item_id not found: {exc}", err=True)
            raise typer.Exit(code=2) from None
        except (ValueError, OSError) as exc:
            # Bad operator input: an allowed call with no --transport-fixture, a
            # missing/unreadable fixture file, or invalid fixture JSON
            # (JSONDecodeError is a ValueError subclass).
            typer.echo(f"error:       {exc}", err=True)
            raise typer.Exit(code=2) from None

        # FR-027 operator output surface.
        typer.echo(f"session_id:              {report.session_id}")
        typer.echo(f"eligibility:             {report.eligibility_outcome}")
        typer.echo(
            f"mock_provider_call_id:   {report.mock_provider_call_id if report.mock_provider_call_id else '<none>'}"
        )
        typer.echo(f"final_disposition:       {report.final_disposition.value}")
        typer.echo(f"wall_time_ms:            {report.wall_time_ms}")
        typer.echo(f"artifact_dir:            {report.artifact_dir}")
        typer.echo("artifacts:")
        for path in sorted(report.artifact_dir.iterdir()):
            typer.echo(f"  {path.name}")
    finally:
        conn.close()


def _load_conversation_fixture(path: Path) -> ConversationFixture:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"conversation fixture {path.name!r} is not a JSON object")
    turns: list[ConversationTurn] = []
    for t in raw.get("turns", []):
        if not isinstance(t, dict) or "role" not in t or "text" not in t:
            raise ValueError(
                f"conversation fixture {path.name!r}: every turn needs 'role' and 'text'"
            )
        turns.append(ConversationTurn(role=t["role"], text=t["text"]))
    return ConversationFixture(
        fixture_id=raw.get("fixture_id", path.stem),
        expected_disposition=raw.get("expected_disposition", ""),
        queue_item_ref=raw.get("queue_item_ref", ""),
        turns=turns,
        expected_extraction=raw.get("expected_extraction", {}),
    )


# ---------------------------------------------------------------------------
# Slice 2 — Dataverse subcommands (contracts/cli-slice2.md)
# ---------------------------------------------------------------------------


@app.command(name="discover-crm")
def discover_crm(
    slice2_config_path: Annotated[
        Path,
        typer.Option("--slice2-config", help="Path to config/slice2.toml"),
    ] = _DEFAULT_SLICE2_CONFIG,
    out: Annotated[
        Path | None,
        typer.Option(
            "--out",
            help="Override the output path (defaults to slice2.toml's mapping_artifact)",
        ),
    ] = None,
) -> None:
    """One-time Dataverse metadata discovery (FR-001/FR-004).

    Reads the existing mapping artifact as a scaffold, confirms every mapped table
    and field against live Dataverse, and rewrites the artifact with a fresh
    `_meta.discovered_at` and `approved=false`. A reviewer flips `approved=true`
    on PR before the next write-enabled run.
    """
    try:
        slice2_config = load_slice2_config(slice2_config_path)
    except (FileNotFoundError, ValueError, ValidationError) as exc:
        typer.echo(f"error:       could not load {slice2_config_path}: {exc}", err=True)
        raise typer.Exit(code=2) from None

    try:
        secrets = load_dataverse_secrets()
    except Slice2ConfigError as exc:
        typer.echo(f"error:       {exc}", err=True)
        raise typer.Exit(code=2) from None

    # Discovery reads the configured mapping artifact as its scaffold (the human-
    # reviewed conceptual-to-logical assignments live there), then writes the
    # refreshed result. `--out` only overrides the output path — using it as both
    # input and output would break the first run with a new --out path.
    scaffold_path = Path(slice2_config.dataverse.mapping_artifact)
    artifact_path = out or scaffold_path
    try:
        scaffold = load_mapping(scaffold_path)
    except MappingError as exc:
        typer.echo(f"error:       {exc}", err=True)
        raise typer.Exit(code=2) from None

    clock = SystemClock()
    token_provider = DataverseTokenProvider(secrets)
    client = DataverseClient(
        secrets.env_url,
        token_provider,
        slice2_config.retry,
    )
    try:
        try:
            refreshed = discover(client, scaffold, now_utc_ms=clock.now_utc_ms())
        except (DataverseError, MetadataError) as exc:
            typer.echo(f"error:       discovery failed: {exc}", err=True)
            raise typer.Exit(code=2) from None
    finally:
        client.close()
        token_provider.close()

    body = refreshed.model_dump(by_alias=True, mode="json")
    artifact_path.write_text(
        json.dumps(body, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    typer.echo(f"discovered:  {artifact_path}")
    typer.echo(f"approved:    {refreshed.meta.approved} (flip to true on PR review)")
    typer.echo(f"discovered_at: {refreshed.meta.discovered_at}")


@app.command(name="run-crm")
def run_crm(
    write: Annotated[
        bool,
        typer.Option(
            "--write",
            help=(
                "Enable Dataverse write-back (FR-031). Required in this slice — the "
                "default dry-run path is wired in US2 (T024-T026)."
            ),
        ),
    ] = False,
    queue_item_id: Annotated[
        str | None,
        typer.Option("--queue-item-id", help="Dataverse queue-item GUID to process"),
    ] = None,
    next_ready: Annotated[
        bool,
        typer.Option("--next-ready", help="Process the deterministically-next ready item"),
    ] = False,
    campaign: Annotated[
        str | None,
        typer.Option("--campaign", help="Campaign selector (overrides slice2.toml [run].campaign)"),
    ] = None,
    transport_fixture: Annotated[
        Path,
        typer.Option("--transport-fixture", help="Path to a transport-events JSON fixture"),
    ] = ...,  # type: ignore[assignment]
    conversation_fixture: Annotated[
        Path | None,
        typer.Option(
            "--conversation-fixture",
            help="Path to the scripted conversation JSON (required for connected calls)",
        ),
    ] = None,
    config_path: Annotated[
        Path, typer.Option("--config", help="Path to slice1.toml")
    ] = _DEFAULT_CONFIG_PATH,
    slice2_config_path: Annotated[
        Path,
        typer.Option("--slice2-config", help="Path to config/slice2.toml"),
    ] = _DEFAULT_SLICE2_CONFIG,
) -> None:
    """Process exactly one Dataverse queue item (FR-032).

    Requires `--write` in this slice. The contract's dry-run default (FR-031) is
    intentionally not yet wired — that work lives in US2 (T024-T026) where the
    runner gains a dry-run capture adapter and the planned-write-back artifact
    path. Until that lands, `run-crm` without `--write` exits 2 with a pointer.
    """
    if not write:
        typer.echo(
            "error:       dry-run is not yet implemented (US2 / T024-T026). Pass --write "
            "to run the write-enabled path.",
            err=True,
        )
        raise typer.Exit(code=2)

    # Load configs before building the selector so `--next-ready` can fall back
    # to the configured `[run].campaign` when `--campaign` is omitted.
    try:
        slice1_config = load_config(config_path)
        slice2_config = load_slice2_config(slice2_config_path)
    except (FileNotFoundError, ValueError, ValidationError) as exc:
        typer.echo(f"error:       config load failed: {exc}", err=True)
        raise typer.Exit(code=2) from None

    if queue_item_id is not None and not _GUID_RE.match(queue_item_id):
        typer.echo(
            f"error:       --queue-item-id {queue_item_id!r} is not a valid "
            "Dataverse GUID (expected 8-4-4-4-12 hex digits, e.g. "
            "22222222-2222-2222-2222-222222222222).",
            err=True,
        )
        raise typer.Exit(code=2)

    effective_campaign = campaign or slice2_config.run.campaign
    selector = _build_selector(
        queue_item_id=queue_item_id,
        next_ready=next_ready,
        campaign=effective_campaign,
    )
    if selector is None:
        typer.echo(
            "error:       provide exactly one of --queue-item-id or --next-ready",
            err=True,
        )
        raise typer.Exit(code=2)
    # `--next-ready` requires a non-empty campaign so the queue-loader's
    # selector carries the scope the contract demands (cli-slice2.md). The
    # loader's NextReady path filters by `queue.campaign` when the mapping
    # carries that field, and raises `QueueLoadError` when it doesn't — this
    # CLI gate just turns a missing operator argument into a clean exit code
    # instead of a deeper failure.
    if next_ready and not effective_campaign:
        typer.echo(
            "error:       --next-ready requires --campaign (or a non-empty "
            "[run].campaign in slice2.toml).",
            err=True,
        )
        raise typer.Exit(code=2)

    try:
        secrets = load_dataverse_secrets()
    except Slice2ConfigError as exc:
        typer.echo(f"error:       {exc}", err=True)
        raise typer.Exit(code=2) from None

    clock = SystemClock()
    token_provider = DataverseTokenProvider(secrets)
    client = DataverseClient(secrets.env_url, token_provider, slice2_config.retry)
    conn = store.connect(slice1_config.state.db)
    try:
        report = run_one_crm_item(
            selector=selector,
            transport_fixture=transport_fixture,
            conversation_fixture=conversation_fixture,
            slice1_config=slice1_config,
            slice2_config=slice2_config,
            client=client,
            conn=conn,
            clock=clock,
        )
    finally:
        conn.close()
        client.close()
        token_provider.close()

    typer.echo(f"exit_status:           {report.exit_status}")
    if report.session_id:
        typer.echo(f"session_id:            {report.session_id}")
    if report.final_disposition:
        typer.echo(f"final_disposition:     {report.final_disposition.value}")
    if report.queue_item_id:
        typer.echo(f"queue_item_id:         {report.queue_item_id}")
    if report.artifact_dir:
        typer.echo(f"artifact_dir:          {report.artifact_dir}")
    if report.warnings:
        typer.echo("warnings:")
        for w in report.warnings:
            typer.echo(f"  {w.code}: {w.message}")
    if report.message:
        typer.echo(f"message:               {report.message}")

    raise typer.Exit(code=_EXIT_CODE.get(report.exit_status, 2))


def _build_selector(
    *,
    queue_item_id: str | None,
    next_ready: bool,
    campaign: str | None,
) -> QueueSelector | None:
    if bool(queue_item_id) == bool(next_ready):
        return None
    if queue_item_id:
        return ExplicitId(queue_item_id)
    return NextReady(campaign or "")
