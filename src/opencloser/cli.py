"""Typer CLI — Slice 1 operator surface (FR-025 / FR-026 / FR-027).

Three subcommands:
- `init-state`           — create state DB and apply schema (idempotent)
- `load-queue-item`      — INSERT a queue item from a JSON fixture
- `run-one`              — process exactly one queue record end-to-end
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Annotated

import typer

from opencloser.core.clock import SystemClock
from opencloser.core.config import load_config
from opencloser.core.orchestrator import QueueItemNotFound, process_one_queue_item
from opencloser.eligibility.evaluator import BuiltinEligibilityEvaluator
from opencloser.models import QueueItem
from opencloser.persona.alf_appointment_setter import ALFAppointmentSetterPersona
from opencloser.persona.base import ConversationFixture, ConversationTurn
from opencloser.state import store
from opencloser.transport.mock import FixtureDrivenTransport

app = typer.Typer(
    name="opencloser",
    help="openCloser Slice 1 — Mock Call, Mock CRM.",
    no_args_is_help=True,
)


_DEFAULT_CONFIG_PATH = Path("config/slice1.toml")


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
    conn = store.connect(config.state.db)
    try:
        # Locate transport fixtures dir + fixture id.
        if transport_fixture is not None:
            transport_dir = transport_fixture.parent
            transport_fixture_id = transport_fixture.stem
        else:
            transport_dir = Path("tests/fixtures/transport_events")
            transport_fixture_id = None

        # Load conversation fixture if provided.
        conversation = (
            _load_conversation_fixture(conversation_fixture) if conversation_fixture else None
        )

        try:
            report = process_one_queue_item(
                queue_item_id,
                conn=conn,
                config=config,
                eligibility=BuiltinEligibilityEvaluator(),
                transport=FixtureDrivenTransport(transport_dir),
                persona=ALFAppointmentSetterPersona(),
                conversation_fixture=conversation,
                transport_fixture_id=transport_fixture_id,
            )
        except QueueItemNotFound as exc:
            typer.echo(f"error:       queue_item_id not found: {exc}", err=True)
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
    turns = [ConversationTurn(role=t["role"], text=t["text"]) for t in raw.get("turns", [])]
    return ConversationFixture(
        fixture_id=raw.get("fixture_id", path.stem),
        expected_disposition=raw.get("expected_disposition", ""),
        queue_item_ref=raw.get("queue_item_ref", ""),
        turns=turns,
        expected_extraction=raw.get("expected_extraction", {}),
    )


_ = sqlite3  # keep import for state-level callers; CLI itself doesn't use it directly
