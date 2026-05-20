"""Orchestrator-level idempotency tests (T055) — duplicate-event no-op + conflicting late event.

These exercise the orchestrator's FR-019 + FR-020 invariants end-to-end against the real
state store, but at the unit-test layer (no fixture-file assumptions — we build small
in-memory fixtures here)."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from opencloser.core.clock import FrozenClock
from opencloser.core.orchestrator import process_one_queue_item
from opencloser.crm.mock import MockWriteBackAdapter
from opencloser.eligibility.evaluator import BuiltinEligibilityEvaluator
from opencloser.models import (
    ArtifactsConfig,
    CallableStatus,
    CallWindowConfig,
    Disposition,
    EligibilityConfig,
    PersonaConfig,
    QueueItem,
    SliceConfig,
    StateConfig,
)
from opencloser.persona.alf_appointment_setter import (
    CANONICAL_DISCLOSURE,
    ALFAppointmentSetterPersona,
)
from opencloser.persona.base import ConversationFixture, ConversationTurn
from opencloser.state import store
from opencloser.transport.mock import FixtureDrivenTransport

pytestmark = pytest.mark.module("core")


def _config(artifact_dir: Path, db_path: Path) -> SliceConfig:
    return SliceConfig(
        call_window=CallWindowConfig(start="09:00", end="20:00"),
        eligibility=EligibilityConfig(max_attempts=5, default_timezone="America/Los_Angeles"),
        artifacts=ArtifactsConfig(dir=str(artifact_dir)),
        persona=PersonaConfig(version="alf-appointment-setter@0.1.0"),
        state=StateConfig(db=str(db_path)),
    )


def _conv() -> ConversationFixture:
    return ConversationFixture(
        fixture_id="cb",
        expected_disposition="interested_callback_requested",
        queue_item_ref="q1",
        turns=[
            ConversationTurn(role="persona", text=CANONICAL_DISCLOSURE),
            ConversationTurn(role="contact", text="I'm the owner. Call me back Thursday at 2 PM."),
        ],
        expected_extraction={},
    )


def _write_fixture(d: Path, name: str, events: list[dict]) -> None:
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.json").write_text(
        json.dumps({"fixture_id": name, "events": events}), encoding="utf-8"
    )


def _seed(conn: sqlite3.Connection) -> None:
    store.insert_queue_item(
        conn,
        QueueItem(
            queue_item_id="q1",
            facility_name="Sunset",
            phone_number="+15555550100",
            timezone="America/Los_Angeles",
            attempt_count=0,
            callable_status=CallableStatus.READY,
        ),
    )


def test_orchestrator_duplicate_events_are_no_ops(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path, tmp_path: Path
) -> None:
    """FR-019: redelivered events leave state, write-backs, and attempt_count unchanged."""
    _seed(tmp_state_db)
    _write_fixture(
        tmp_path / "transport",
        "dup",
        [
            {"event_id": "e1", "type": "connected", "timestamp": "2026-05-19T17:00:00.000Z"},
            {"event_id": "e2", "type": "completed", "timestamp": "2026-05-19T17:00:45.000Z"},
            {"event_id": "e1", "type": "connected", "timestamp": "2026-05-19T17:00:00.000Z"},
            {"event_id": "e2", "type": "completed", "timestamp": "2026-05-19T17:00:45.000Z"},
        ],
    )
    report = process_one_queue_item(
        "q1",
        conn=tmp_state_db,
        config=_config(tmp_artifact_dir, tmp_path / "db"),
        eligibility=BuiltinEligibilityEvaluator(),
        transport=FixtureDrivenTransport(tmp_path / "transport"),
        persona=ALFAppointmentSetterPersona(),
        crm=MockWriteBackAdapter(tmp_state_db),
        conversation_fixture=_conv(),
        transport_fixture_id="dup",
        clock=FrozenClock(datetime(2026, 5, 19, 19, 0, 0, tzinfo=UTC)),
    )
    assert report.final_disposition is Disposition.INTERESTED_CALLBACK_REQUESTED

    # mock_call_events: exactly 2 rows (composite PK enforced by SQLite; duplicates are no-ops).
    n = tmp_state_db.execute("SELECT COUNT(*) AS n FROM mock_call_events;").fetchone()["n"]
    assert n == 2
    # phone_call_activities: exactly 1.
    n = tmp_state_db.execute("SELECT COUNT(*) AS n FROM phone_call_activities;").fetchone()["n"]
    assert n == 1
    # task_payloads: exactly 1.
    n = tmp_state_db.execute("SELECT COUNT(*) AS n FROM task_payloads;").fetchone()["n"]
    assert n == 1
    # queue_items.attempt_count == 1 (FR-021).
    qi = store.get_queue_item(tmp_state_db, "q1")
    assert qi is not None and qi.attempt_count == 1


def test_orchestrator_late_conflicting_event_audited_only(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path, tmp_path: Path
) -> None:
    """FR-020: a late `failed` after `completed` is audit-logged; finalized disposition is preserved."""
    _seed(tmp_state_db)
    _write_fixture(
        tmp_path / "transport",
        "conflict",
        [
            {"event_id": "e1", "type": "connected", "timestamp": "2026-05-19T17:00:00.000Z"},
            {"event_id": "e2", "type": "completed", "timestamp": "2026-05-19T17:00:45.000Z"},
            {
                "event_id": "e3_late",
                "type": "failed",
                "timestamp": "2026-05-19T17:00:50.000Z",
                "payload": {"failure_reason": "transport_error"},
            },
        ],
    )
    report = process_one_queue_item(
        "q1",
        conn=tmp_state_db,
        config=_config(tmp_artifact_dir, tmp_path / "db"),
        eligibility=BuiltinEligibilityEvaluator(),
        transport=FixtureDrivenTransport(tmp_path / "transport"),
        persona=ALFAppointmentSetterPersona(),
        crm=MockWriteBackAdapter(tmp_state_db),
        conversation_fixture=_conv(),
        transport_fixture_id="conflict",
        clock=FrozenClock(datetime(2026, 5, 19, 19, 0, 0, tzinfo=UTC)),
    )
    assert report.final_disposition is Disposition.INTERESTED_CALLBACK_REQUESTED

    # Conflicting event audited.
    audits = tmp_state_db.execute(
        "SELECT conflicting_event_type, preserved_disposition FROM conflicting_event_audit_records;"
    ).fetchall()
    assert len(audits) == 1
    assert audits[0]["conflicting_event_type"] == "failed"
    assert audits[0]["preserved_disposition"] == "interested_callback_requested"

    # Conflicting-events artifact written.
    assert (report.artifact_dir / "conflicting-events.json").exists()
