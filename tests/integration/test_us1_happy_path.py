"""US1 Story 1 — Run the full mock loop on one eligible ALF queue record (P1, MVP).

Independent Test (per spec §Story 1): load alf-prospect-001, run with the
interested_callback_requested conversation fixture + connected transport fixture, and
verify (a)-(f) of the spec's Independent Test bullet.
"""

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

# Fixtures are committed under tests/fixtures/.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_QUEUE_ITEM_FIXTURE = _REPO_ROOT / "tests/fixtures/queue_items/alf-prospect-001.json"
_CONVERSATION_FIXTURE = (
    _REPO_ROOT / "tests/fixtures/conversations/interested_callback_requested.json"
)
_TRANSPORT_FIXTURES = _REPO_ROOT / "tests/fixtures/transport_events"


def _config(artifact_dir: Path, db_path: Path) -> SliceConfig:
    return SliceConfig(
        call_window=CallWindowConfig(start="09:00", end="20:00"),
        eligibility=EligibilityConfig(max_attempts=5, default_timezone="America/Los_Angeles"),
        artifacts=ArtifactsConfig(dir=str(artifact_dir)),
        persona=PersonaConfig(version="alf-appointment-setter@0.1.0"),
        state=StateConfig(db=str(db_path)),
    )


def _load_queue_item() -> QueueItem:
    return QueueItem.model_validate_json(_QUEUE_ITEM_FIXTURE.read_text(encoding="utf-8"))


def _load_conversation() -> ConversationFixture:
    raw = json.loads(_CONVERSATION_FIXTURE.read_text(encoding="utf-8"))
    return ConversationFixture(
        fixture_id=raw["fixture_id"],
        expected_disposition=raw["expected_disposition"],
        queue_item_ref=raw["queue_item_ref"],
        turns=[ConversationTurn(role=t["role"], text=t["text"]) for t in raw["turns"]],
        expected_extraction=raw["expected_extraction"],
    )


def test_us1_story1_happy_path_end_to_end(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path, tmp_path: Path
) -> None:
    """Spec §Story 1 Independent Test — Acceptance Scenario 1 ("interested, callback requested")."""
    # Setup: load alf-prospect-001 into the temp DB.
    store.insert_queue_item(tmp_state_db, _load_queue_item())

    # Run.
    report = process_one_queue_item(
        "alf-prospect-001",
        conn=tmp_state_db,
        config=_config(tmp_artifact_dir, tmp_path / "slice1.db"),
        eligibility=BuiltinEligibilityEvaluator(),
        transport=FixtureDrivenTransport(_TRANSPORT_FIXTURES),
        persona=ALFAppointmentSetterPersona(),
        crm=MockWriteBackAdapter(tmp_state_db),
        conversation_fixture=_load_conversation(),
        transport_fixture_id="connected",
        clock=FrozenClock(datetime(2026, 5, 19, 19, 0, 0, tzinfo=UTC)),
    )

    # (a) final disposition matches the scripted conversation outcome.
    assert report.final_disposition is Disposition.INTERESTED_CALLBACK_REQUESTED

    # (b) session row + event rows persisted in local state.
    sess = store.get_session(tmp_state_db, report.session_id)
    assert sess is not None
    events = store.list_mock_call_events(tmp_state_db, report.session_id)
    assert {e.event_type.value for e in events} == {"connected", "completed"}

    # (c) Phone Call-like activity payload exists.
    n = tmp_state_db.execute("SELECT COUNT(*) AS n FROM phone_call_activities;").fetchone()["n"]
    assert n == 1

    # (d) Queue-status update payload exists.
    n = tmp_state_db.execute("SELECT COUNT(*) AS n FROM queue_status_updates;").fetchone()["n"]
    assert n == 1

    # (e) Task payload exists with preferred_callback_window (and captured_email when present).
    row = tmp_state_db.execute(
        "SELECT task_kind, preferred_callback_window FROM task_payloads WHERE session_id = ?;",
        (report.session_id,),
    ).fetchone()
    assert row is not None
    assert row["task_kind"] == "callback"
    assert row["preferred_callback_window"] is not None

    # (f) Inspectable JSON artifacts on disk.
    for name in (
        "session-result.json",
        "writeback.json",
        "task.json",
        "transcript.txt",
        "eligibility-decision.json",
    ):
        assert (report.artifact_dir / name).exists(), f"missing artifact {name}"

    # SC-001: wall_time_ms is non-negative and well under 60 seconds for a fixture run.
    assert 0 <= report.wall_time_ms < 60_000

    # SC-005 anchor: re-running with the SAME inputs from the same temp dir produces byte-identical
    # session-result.json (different session_id will differ, so re-run uses new dir).
    # The basic determinism property is covered by test_artifacts_writer.py; this integration
    # test confirms the happy-path artifacts are well-formed JSON.
    parsed = json.loads((report.artifact_dir / "session-result.json").read_text(encoding="utf-8"))
    assert parsed["final_disposition"] == "interested_callback_requested"
    assert parsed["callback_requested"] is True
    assert parsed["preferred_callback_window"] is not None
    assert parsed["schema_version"] == "slice1-v1"
