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
from opencloser.crm.dataverse.mapping import MappingError, MappingTranslator, load_mapping
from opencloser.crm.dataverse.metadata import MetadataError, discover
from opencloser.crm.dataverse.queue_loader import ExplicitId, NextReady, QueueSelector
from opencloser.crm.mock import MockWriteBackAdapter
from opencloser.eligibility.evaluator import BuiltinEligibilityEvaluator
from opencloser.models import DataverseSecrets, QueueItem, RunMode
from opencloser.persona.alf_appointment_setter import ALFAppointmentSetterPersona
from opencloser.persona.base import ConversationFixture, ConversationTurn
from opencloser.slice2.resume import ResumeError, resume_session
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
    except (FileNotFoundError, ValueError) as exc:
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
                "Enable Dataverse write-back (FR-031). Without this flag, run-crm "
                "operates in dry-run mode: validates the mapping, exercises the "
                "persona + transport, and captures the planned write-back as local "
                "artifacts — zero create or update operations are issued against "
                "Dataverse (SC-002, SC-013)."
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
        Path | None,
        typer.Option(
            "--transport-fixture",
            help=(
                "Path to a transport-events JSON fixture. Required unless --resume "
                "is supplied (resume replays persisted write-back payloads and does "
                "not re-run the orchestrator)."
            ),
        ),
    ] = None,
    resume: Annotated[
        str | None,
        typer.Option(
            "--resume",
            help=(
                "Session ID of a `resume_needed` write-back to replay (FR-023). "
                "Routes to the resume coordinator and skips queue load + persona + "
                "transport — only the missing emit_* operations are issued. "
                "Requires --write."
            ),
        ),
    ] = None,
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

    Run mode follows FR-031: no ``--write`` means dry-run (the default — validate
    mapping, exercise persona + transport, capture planned write-back artifacts,
    zero CRM mutations). ``--write`` enables the write-enabled path. There is no
    way to mutate Dataverse without ``--write`` (SC-013).

    ``--resume <session-id>`` (FR-023, T033): when supplied, the CLI replays
    only the missing ``emit_*`` operations for a ``resume_needed`` session
    using the persisted ``writeback.json`` and ``writeback_progress`` rows.
    Requires ``--write`` (resume is by definition a write-back continuation)
    and is incompatible with ``--queue-item-id`` / ``--next-ready`` /
    ``--transport-fixture`` (resume does not re-run the orchestrator).
    """
    run_mode = RunMode.WRITE_ENABLED if write else RunMode.DRY_RUN

    if resume is not None:
        if not write:
            typer.echo(
                "error:       --resume requires --write (resume is a write-back continuation)",
                err=True,
            )
            raise typer.Exit(code=2)
        if queue_item_id or next_ready or transport_fixture is not None:
            typer.echo(
                "error:       --resume is incompatible with --queue-item-id / --next-ready / "
                "--transport-fixture (resume operates on persisted write-back payloads only)",
                err=True,
            )
            raise typer.Exit(code=2)
        # Copilot PR #9 review: warn when other orchestrator-input flags
        # are silently ignored. These have no effect in resume mode because
        # the resume coordinator does not re-run process_one_queue_item.
        if conversation_fixture is not None:
            typer.echo(
                "warning:     --conversation-fixture is ignored when --resume is set "
                "(resume does not re-run the orchestrator)",
                err=True,
            )
        if campaign is not None:
            typer.echo(
                "warning:     --campaign is ignored when --resume is set "
                "(resume operates on the session id only)",
                err=True,
            )
        _run_crm_resume(
            session_id=resume,
            config_path=config_path,
            slice2_config_path=slice2_config_path,
        )
        return

    if transport_fixture is None:
        typer.echo(
            "error:       --transport-fixture is required when --resume is not set",
            err=True,
        )
        raise typer.Exit(code=2)

    slice1_config, slice2_config = _load_run_crm_configs(config_path, slice2_config_path)
    selector = _build_run_crm_selector(
        queue_item_id=queue_item_id,
        next_ready=next_ready,
        campaign=campaign or slice2_config.run.campaign,
    )

    # FR-031 + spec §Edge Cases "Dry-run requested but write credentials are
    # absent": missing Dataverse secrets MUST NOT block the dry-run path
    # (Codex PR #7 review). In write-enabled mode the same error is fatal.
    # When secrets are missing in dry-run, we still construct a placeholder
    # client so the runner's downstream code path is unchanged — the runner's
    # `_verify_readiness(dry_run=True)` catches any auth/connectivity failure
    # from the live `verify()` call and treats it as non-fatal per the
    # `contracts/metadata-discovery-verification.md` §5 rule.
    try:
        secrets = load_dataverse_secrets()
    except Slice2ConfigError as exc:
        if run_mode is RunMode.WRITE_ENABLED:
            typer.echo(f"error:       {exc}", err=True)
            raise typer.Exit(code=2) from None
        typer.echo(
            f"warning:     {exc} — proceeding in dry-run mode (write-back disabled, "
            "any Dataverse read will fail late and surface as a queue-load error)",
            err=True,
        )
        secrets = DataverseSecrets(
            tenant_id="dry-run-placeholder",
            client_id="dry-run-placeholder",
            client_secret="dry-run-placeholder",
            env_url="https://dry-run-placeholder.crm.dynamics.com",
        )

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
            run_mode=run_mode,
        )
    finally:
        conn.close()
        client.close()
        token_provider.close()

    _print_crm_report(report)

    raise typer.Exit(code=_EXIT_CODE.get(report.exit_status, 2))


def _load_run_crm_configs(config_path: Path, slice2_config_path: Path):
    """Load both config files for `run-crm`, normalizing schema/file errors."""
    try:
        return load_config(config_path), load_slice2_config(slice2_config_path)
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(f"error:       config load failed: {exc}", err=True)
        raise typer.Exit(code=2) from None


def _build_run_crm_selector(
    *,
    queue_item_id: str | None,
    next_ready: bool,
    campaign: str | None,
) -> QueueSelector:
    if queue_item_id is not None and not _GUID_RE.match(queue_item_id):
        typer.echo(
            f"error:       --queue-item-id {queue_item_id!r} is not a valid "
            "Dataverse GUID (expected 8-4-4-4-12 hex digits, e.g. "
            "22222222-2222-2222-2222-222222222222).",
            err=True,
        )
        raise typer.Exit(code=2)

    selector = _build_selector(
        queue_item_id=queue_item_id,
        next_ready=next_ready,
        campaign=campaign,
    )
    if selector is None:
        typer.echo(
            "error:       provide exactly one of --queue-item-id or --next-ready",
            err=True,
        )
        raise typer.Exit(code=2)

    if next_ready and not campaign:
        typer.echo(
            "error:       --next-ready requires --campaign (or a non-empty "
            "[run].campaign in slice2.toml).",
            err=True,
        )
        raise typer.Exit(code=2)
    return selector


def _run_crm_resume(
    *,
    session_id: str,
    config_path: Path,
    slice2_config_path: Path,
) -> None:
    """T033 — `run-crm --resume <session-id>` entry point. Loads configs,
    short-circuits on a non-replayable progress state BEFORE touching
    Dataverse secrets (so a finalized session can be re-invoked without
    credentials per FR-021 idempotency — Codex PR #9 P1), then constructs
    the Dataverse client + mapping translator and routes to the FR-023
    resume coordinator.

    Exit codes mirror `run-crm`'s normal table: completed → 0,
    no-resume-needed → 0 (FR-021), blocked → 1, failed → 2.
    """
    from opencloser.models import RunStatus

    slice1_config, slice2_config = _load_run_crm_configs(config_path, slice2_config_path)

    # PRE-FLIGHT: check writeback_progress BEFORE loading Dataverse secrets.
    # An already-`completed` session is a true no-op and must not fail just
    # because the operator running the resume happens to be missing creds.
    # A `blocked` session is permanently non-resumable; surface that early
    # too — no Dataverse round-trip is needed to know it (Codex PR #9 P1).
    conn = store.connect(slice1_config.state.db)
    try:
        progress = store.get_writeback_progress(conn, session_id)
        if progress is None:
            typer.echo(
                f"error:       resume pre-flight failed: session {session_id!r} "
                "has no writeback_progress row; nothing to resume",
                err=True,
            )
            raise typer.Exit(code=2)
        if progress.run_status is RunStatus.COMPLETED:
            typer.echo("exit_status:           no-resume-needed")
            typer.echo(f"session_id:            {session_id}")
            typer.echo(
                "message:               session is already completed; no replay "
                "performed (FR-021)"
            )
            raise typer.Exit(code=0)
        if progress.run_status is RunStatus.BLOCKED:
            typer.echo("exit_status:           blocked")
            typer.echo(f"session_id:            {session_id}")
            typer.echo(
                f"message:               session is in 'blocked'; a permanent error "
                f"({progress.last_error!r}) stopped the original run. Resume cannot "
                "recover."
            )
            raise typer.Exit(code=1)
        if progress.run_status is RunStatus.IN_PROGRESS:
            typer.echo("exit_status:           failed")
            typer.echo(f"session_id:            {session_id}")
            typer.echo(
                "message:               session is in 'in_progress'; another run "
                "may still be working on it. Investigate writeback_progress."
                "updated_at before retrying."
            )
            raise typer.Exit(code=2)
        # RESUME_NEEDED → fall through to the live-Dataverse path below.
    except typer.Exit:
        conn.close()
        raise
    except Exception:
        conn.close()
        raise

    try:
        secrets = load_dataverse_secrets()
    except Slice2ConfigError as exc:
        conn.close()
        typer.echo(f"error:       {exc}", err=True)
        raise typer.Exit(code=2) from None

    # Load + validate the mapping artifact — resume requires the same approved
    # mapping the original run used. Schema/approval errors are operator-
    # visible-blocked (mirrors `_verify_readiness`'s first two gates).
    try:
        mapping = load_mapping(slice2_config.dataverse.mapping_artifact)
    except MappingError as exc:
        conn.close()
        typer.echo(f"error:       mapping artifact error: {exc}", err=True)
        raise typer.Exit(code=2) from None
    if not mapping.meta.approved:
        conn.close()
        typer.echo(
            "error:       mapping artifact "
            f"{slice2_config.dataverse.mapping_artifact!r} is not approved; "
            "re-run `discover-crm` and have a reviewer flip _meta.approved to true",
            err=True,
        )
        raise typer.Exit(code=2)
    translator = MappingTranslator(mapping)

    clock = SystemClock()
    token_provider = DataverseTokenProvider(secrets)
    client = DataverseClient(secrets.env_url, token_provider, slice2_config.retry)
    try:
        try:
            result = resume_session(
                session_id=session_id,
                conn=conn,
                artifact_root=Path(slice1_config.artifacts.dir),
                client=client,
                translator=translator,
                task_owners=slice2_config.task_owners,
                clock=clock,
            )
        except ResumeError as exc:
            typer.echo(f"error:       resume pre-flight failed: {exc}", err=True)
            raise typer.Exit(code=2) from None
    finally:
        conn.close()
        client.close()
        token_provider.close()

    typer.echo(f"exit_status:           {result.exit_status}")
    typer.echo(f"session_id:            {result.session_id}")
    if result.artifact_dir is not None:
        typer.echo(f"artifact_dir:          {result.artifact_dir}")
    if result.operations_replayed is not None:
        typer.echo(
            f"operations_replayed:   {', '.join(result.operations_replayed) or 'none'}"
        )
    if result.message:
        typer.echo(f"message:               {result.message}")

    code = {
        "completed": 0,
        "no-resume-needed": 0,
        "blocked": 1,
        "resume_needed": 2,
        "failed": 2,
    }.get(result.exit_status, 2)
    raise typer.Exit(code=code)


def _print_crm_report(report) -> None:
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
