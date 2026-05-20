"""Unit tests for the orchestrator's happy-path flow (T033).

Exercises end-to-end against a temp state store + temp artifact dir + real persona +
fixture-driven transport. Stubs nothing — this is a small integration test in unit
form to keep the orchestrator's wiring honest.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from opencloser.core.clock import FrozenClock
from opencloser.core.orchestrator import QueueItemNotFound, process_one_queue_item
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


def _at_noon_pacific() -> FrozenClock:
    # 2026-05-19 19:00 UTC = 12:00 Pacific (UTC-7 DST).
    return FrozenClock(datetime(2026, 5, 19, 19, 0, 0, tzinfo=UTC))


def _seed_eligible(conn: sqlite3.Connection) -> None:
    store.insert_queue_item(
        conn,
        QueueItem(
            queue_item_id="q1",
            facility_name="Sunset Ridge",
            phone_number="+15555550100",
            timezone="America/Los_Angeles",
            attempt_count=0,
            callable_status=CallableStatus.READY,
        ),
    )


def _connected_fixture(tmp_path: Path) -> None:
    (tmp_path / "connected.json").write_text(
        json.dumps(
            {
                "fixture_id": "connected",
                "events": [
                    {
                        "event_id": "evt_1",
                        "type": "connected",
                        "timestamp": "2026-05-19T17:00:00.000Z",
                    },
                    {
                        "event_id": "evt_2",
                        "type": "completed",
                        "timestamp": "2026-05-19T17:00:30.000Z",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def _conversation_fixture() -> ConversationFixture:
    return ConversationFixture(
        fixture_id="interested_callback",
        expected_disposition="interested_callback_requested",
        queue_item_ref="q1",
        turns=[
            ConversationTurn(role="persona", text=CANONICAL_DISCLOSURE),
            ConversationTurn(role="contact", text="Sure, I'm the owner of Sunset Ridge."),
            ConversationTurn(role="persona", text="Great. What would be a good callback time?"),
            ConversationTurn(role="contact", text="Call me back Thursday at 2 PM please."),
        ],
        expected_extraction={},
    )


# ---------------------------------------------------------------------------
# Happy path: interested_callback_requested
# ---------------------------------------------------------------------------


def test_happy_path_callback_requested(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path, tmp_path: Path
) -> None:
    _seed_eligible(tmp_state_db)
    (tmp_path / "transport").mkdir(exist_ok=True)
    _connected_fixture(tmp_path / "transport")

    report = process_one_queue_item(
        "q1",
        conn=tmp_state_db,
        config=_config(tmp_artifact_dir, tmp_path / "db"),
        eligibility=BuiltinEligibilityEvaluator(),
        transport=FixtureDrivenTransport(tmp_path / "transport"),
        persona=ALFAppointmentSetterPersona(),
        conversation_fixture=_conversation_fixture(),
        transport_fixture_id="connected",
        clock=_at_noon_pacific(),
    )

    assert report.eligibility_outcome == "allow"
    assert report.final_disposition is Disposition.INTERESTED_CALLBACK_REQUESTED
    assert report.mock_provider_call_id is not None and report.mock_provider_call_id.startswith(
        "call_"
    )

    # Artifacts exist.
    assert (report.artifact_dir / "session-result.json").exists()
    assert (report.artifact_dir / "writeback.json").exists()
    assert (report.artifact_dir / "task.json").exists()
    assert (report.artifact_dir / "transcript.txt").exists()
    assert (report.artifact_dir / "eligibility-decision.json").exists()
    assert not (report.artifact_dir / "conflicting-events.json").exists()

    # Session finalized.
    sess = store.get_session(tmp_state_db, report.session_id)
    assert sess is not None
    assert sess.final_disposition is Disposition.INTERESTED_CALLBACK_REQUESTED
    assert sess.persona_version == "alf-appointment-setter@0.1.0"

    # Attempt count incremented exactly once.
    queue = store.get_queue_item(tmp_state_db, "q1")
    assert queue is not None
    assert queue.attempt_count == 1


# ---------------------------------------------------------------------------
# Block path: eligibility fails (DNC flag)
# ---------------------------------------------------------------------------


def test_block_path_dnc(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path, tmp_path: Path
) -> None:
    store.insert_queue_item(
        tmp_state_db,
        QueueItem(
            queue_item_id="q_dnc",
            facility_name="Sunset Ridge",
            phone_number="+15555550100",
            timezone="America/Los_Angeles",
            attempt_count=0,
            dnc_flag=True,  # fails rule (d)
            callable_status=CallableStatus.READY,
        ),
    )
    (tmp_path / "transport").mkdir(exist_ok=True)

    report = process_one_queue_item(
        "q_dnc",
        conn=tmp_state_db,
        config=_config(tmp_artifact_dir, tmp_path / "db"),
        eligibility=BuiltinEligibilityEvaluator(),
        transport=FixtureDrivenTransport(tmp_path / "transport"),
        persona=ALFAppointmentSetterPersona(),
        conversation_fixture=None,
        transport_fixture_id=None,
        clock=_at_noon_pacific(),
    )

    assert report.eligibility_outcome == "block"
    assert report.final_disposition is Disposition.BLOCKED
    assert report.mock_provider_call_id is None

    # No Phone Call activity for blocked sessions (FR-017).
    n = tmp_state_db.execute("SELECT COUNT(*) AS n FROM phone_call_activities;").fetchone()["n"]
    assert n == 0
    # Queue-status update always emitted (FR-029).
    n = tmp_state_db.execute("SELECT COUNT(*) AS n FROM queue_status_updates;").fetchone()["n"]
    assert n == 1
    # No task payload.
    n = tmp_state_db.execute("SELECT COUNT(*) AS n FROM task_payloads;").fetchone()["n"]
    assert n == 0
    # attempt_count unchanged.
    qi = store.get_queue_item(tmp_state_db, "q_dnc")
    assert qi is not None and qi.attempt_count == 0


# ---------------------------------------------------------------------------
# QueueItemNotFound
# ---------------------------------------------------------------------------


def test_unknown_queue_item_raises(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path, tmp_path: Path
) -> None:
    (tmp_path / "transport").mkdir(exist_ok=True)
    with pytest.raises(QueueItemNotFound):
        process_one_queue_item(
            "does_not_exist",
            conn=tmp_state_db,
            config=_config(tmp_artifact_dir, tmp_path / "db"),
            eligibility=BuiltinEligibilityEvaluator(),
            transport=FixtureDrivenTransport(tmp_path / "transport"),
            persona=ALFAppointmentSetterPersona(),
            conversation_fixture=None,
            transport_fixture_id=None,
            clock=_at_noon_pacific(),
        )
