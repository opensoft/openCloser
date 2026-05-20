"""US3 Story 3 — Simulate every Slice 1 call path, including duplicates (P2).

Covers each transport path (`no_answer`, `voicemail`, `failed`), the duplicate-event
no-op (FR-019), and the conflicting-late-event audit channel (FR-020).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from opencloser.core.clock import FrozenClock
from opencloser.core.orchestrator import process_one_queue_item
from opencloser.eligibility.evaluator import BuiltinEligibilityEvaluator
from opencloser.models import (
    ArtifactsConfig,
    CallWindowConfig,
    Disposition,
    EligibilityConfig,
    PersonaConfig,
    QueueItem,
    SliceConfig,
    StateConfig,
)
from opencloser.persona.alf_appointment_setter import ALFAppointmentSetterPersona
from opencloser.persona.base import ConversationFixture, ConversationTurn
from opencloser.state import store
from opencloser.transport.mock import FixtureDrivenTransport

pytestmark = pytest.mark.integration

_REPO = Path(__file__).resolve().parents[2]
_QUEUE = _REPO / "tests/fixtures/queue_items/alf-prospect-001.json"
_CONV = _REPO / "tests/fixtures/conversations/interested_callback_requested.json"
_TRANSPORT = _REPO / "tests/fixtures/transport_events"


def _config(artifact_dir: Path, db_path: Path) -> SliceConfig:
    return SliceConfig(
        call_window=CallWindowConfig(start="09:00", end="20:00"),
        eligibility=EligibilityConfig(max_attempts=5, default_timezone="America/Los_Angeles"),
        artifacts=ArtifactsConfig(dir=str(artifact_dir)),
        persona=PersonaConfig(version="alf-appointment-setter@0.1.0"),
        state=StateConfig(db=str(db_path)),
    )


def _seed() -> QueueItem:
    return QueueItem.model_validate_json(_QUEUE.read_text(encoding="utf-8"))


def _load_conversation() -> ConversationFixture:
    raw = json.loads(_CONV.read_text(encoding="utf-8"))
    return ConversationFixture(
        fixture_id=raw["fixture_id"],
        expected_disposition=raw["expected_disposition"],
        queue_item_ref=raw["queue_item_ref"],
        turns=[ConversationTurn(role=t["role"], text=t["text"]) for t in raw["turns"]],
        expected_extraction=raw["expected_extraction"],
    )


def _clock() -> FrozenClock:
    return FrozenClock(datetime(2026, 5, 19, 19, 0, 0, tzinfo=UTC))


# ---------------------------------------------------------------------------
# Per-terminal-path
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "transport_fixture,expected_disposition",
    [
        ("no_answer", Disposition.NO_ANSWER),
        ("voicemail", Disposition.VOICEMAIL),
        ("failed", Disposition.FAILED),
    ],
)
def test_us3_terminal_paths_no_persona_invocation(
    tmp_state_db: sqlite3.Connection,
    tmp_artifact_dir: Path,
    tmp_path: Path,
    transport_fixture: str,
    expected_disposition: Disposition,
) -> None:
    """Story 3 Acceptance: no_answer / voicemail / failed produce the right disposition without
    invoking the persona; FR-031 says no callback task is emitted for these."""
    store.insert_queue_item(tmp_state_db, _seed())

    report = process_one_queue_item(
        "alf-prospect-001",
        conn=tmp_state_db,
        config=_config(tmp_artifact_dir, tmp_path / "db"),
        eligibility=BuiltinEligibilityEvaluator(),
        transport=FixtureDrivenTransport(_TRANSPORT),
        persona=ALFAppointmentSetterPersona(),
        conversation_fixture=None,
        transport_fixture_id=transport_fixture,
        clock=_clock(),
    )

    assert report.final_disposition is expected_disposition
    # No Task payload for these dispositions per FR-018.
    n = tmp_state_db.execute("SELECT COUNT(*) AS n FROM task_payloads;").fetchone()["n"]
    assert n == 0
    # Phone Call activity still emitted (FR-031 row for no_answer/voicemail/failed = ✓ ✓ —).
    n = tmp_state_db.execute("SELECT COUNT(*) AS n FROM phone_call_activities;").fetchone()["n"]
    assert n == 1
    # No transcript (no connected conversation).
    assert not (report.artifact_dir / "transcript.txt").exists()


# ---------------------------------------------------------------------------
# Duplicate-event no-op
# ---------------------------------------------------------------------------


def test_us3_duplicate_connected_completed_attempt_count_increments_once(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path, tmp_path: Path
) -> None:
    store.insert_queue_item(tmp_state_db, _seed())
    report = process_one_queue_item(
        "alf-prospect-001",
        conn=tmp_state_db,
        config=_config(tmp_artifact_dir, tmp_path / "db"),
        eligibility=BuiltinEligibilityEvaluator(),
        transport=FixtureDrivenTransport(_TRANSPORT),
        persona=ALFAppointmentSetterPersona(),
        conversation_fixture=_load_conversation(),
        transport_fixture_id="duplicate_connected",
        clock=_clock(),
    )

    # attempt_count incremented exactly once per FR-021.
    qi = store.get_queue_item(tmp_state_db, "alf-prospect-001")
    assert qi is not None and qi.attempt_count == 1
    # Exactly one Phone Call activity row.
    n = tmp_state_db.execute("SELECT COUNT(*) AS n FROM phone_call_activities;").fetchone()["n"]
    assert n == 1
    # Exactly one mock_call_events row per distinct (session_id, event_id).
    n = tmp_state_db.execute("SELECT COUNT(*) AS n FROM mock_call_events;").fetchone()["n"]
    assert n == 2  # one for connected, one for completed (duplicates were no-ops)
    # No conflicting-events artifact (duplicates are silent no-ops, not audit events).
    assert not (report.artifact_dir / "conflicting-events.json").exists()


def test_us3_duplicate_callback_event_does_not_emit_second_task(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path, tmp_path: Path
) -> None:
    """Story 3 AS5 / FR-019: a `callback_requested` event redelivered for the same
    session retains the original callback task and does NOT emit a second one."""
    store.insert_queue_item(tmp_state_db, _seed())
    report = process_one_queue_item(
        "alf-prospect-001",
        conn=tmp_state_db,
        config=_config(tmp_artifact_dir, tmp_path / "db"),
        eligibility=BuiltinEligibilityEvaluator(),
        transport=FixtureDrivenTransport(_TRANSPORT),
        persona=ALFAppointmentSetterPersona(),
        conversation_fixture=_load_conversation(),
        transport_fixture_id="duplicate_callback_requested",
        clock=_clock(),
    )

    assert report.final_disposition is Disposition.INTERESTED_CALLBACK_REQUESTED
    # Exactly one task payload despite the redelivered callback_requested event.
    n = tmp_state_db.execute("SELECT COUNT(*) AS n FROM task_payloads;").fetchone()["n"]
    assert n == 1
    # The duplicate is a silent no-op (FR-019), not an FR-020 audit event.
    assert not (report.artifact_dir / "conflicting-events.json").exists()
    n = tmp_state_db.execute(
        "SELECT COUNT(*) AS n FROM conflicting_event_audit_records;"
    ).fetchone()["n"]
    assert n == 0


# ---------------------------------------------------------------------------
# Conflicting late event (FR-020)
# ---------------------------------------------------------------------------


def test_us3_conflicting_failed_after_completed_audited_not_applied(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path, tmp_path: Path
) -> None:
    store.insert_queue_item(tmp_state_db, _seed())
    report = process_one_queue_item(
        "alf-prospect-001",
        conn=tmp_state_db,
        config=_config(tmp_artifact_dir, tmp_path / "db"),
        eligibility=BuiltinEligibilityEvaluator(),
        transport=FixtureDrivenTransport(_TRANSPORT),
        persona=ALFAppointmentSetterPersona(),
        conversation_fixture=_load_conversation(),
        transport_fixture_id="conflicting_failed_after_completed",
        clock=_clock(),
    )

    # Finalized disposition is what the conversation produced (interested_callback_requested),
    # NOT `failed` from the late event.
    assert report.final_disposition is Disposition.INTERESTED_CALLBACK_REQUESTED

    # The late conflicting `failed` event is recorded in the audit channel.
    audit_path = report.artifact_dir / "conflicting-events.json"
    assert audit_path.exists()
    parsed = json.loads(audit_path.read_text(encoding="utf-8"))
    assert len(parsed["events"]) == 1
    assert parsed["events"][0]["conflicting_event_type"] == "failed"
    assert parsed["events"][0]["preserved_disposition"] == "interested_callback_requested"

    # DB-level: one row in conflicting_event_audit_records.
    n = tmp_state_db.execute(
        "SELECT COUNT(*) AS n FROM conflicting_event_audit_records;"
    ).fetchone()["n"]
    assert n == 1
