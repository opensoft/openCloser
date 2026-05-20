"""T070 — SC-006 zero false connected-call activities.

For sessions ending in `no_answer`, `voicemail`, or `failed`, the Phone Call activity
payload MUST NOT claim a connected conversation. We assert this by inspecting the
exported summary text — it must NOT contain the persona's first-utterance phrasing.
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
from opencloser.state import store
from opencloser.transport.mock import FixtureDrivenTransport

pytestmark = pytest.mark.integration

_REPO = Path(__file__).resolve().parents[2]
_QUEUE = _REPO / "tests/fixtures/queue_items/alf-prospect-001.json"
_TRANSPORT = _REPO / "tests/fixtures/transport_events"


def _config(artifact_dir: Path, db_path: Path) -> SliceConfig:
    return SliceConfig(
        call_window=CallWindowConfig(start="09:00", end="20:00"),
        eligibility=EligibilityConfig(max_attempts=5, default_timezone="America/Los_Angeles"),
        artifacts=ArtifactsConfig(dir=str(artifact_dir)),
        persona=PersonaConfig(version="alf-appointment-setter@0.1.0"),
        state=StateConfig(db=str(db_path)),
    )


@pytest.mark.parametrize(
    "fixture_id,expected_disposition",
    [
        ("no_answer", Disposition.NO_ANSWER),
        ("voicemail", Disposition.VOICEMAIL),
        ("failed", Disposition.FAILED),
    ],
)
def test_sc006_no_false_connected_activity(
    tmp_state_db: sqlite3.Connection,
    tmp_artifact_dir: Path,
    tmp_path: Path,
    fixture_id: str,
    expected_disposition: Disposition,
) -> None:
    store.insert_queue_item(
        tmp_state_db, QueueItem.model_validate_json(_QUEUE.read_text(encoding="utf-8"))
    )
    report = process_one_queue_item(
        "alf-prospect-001",
        conn=tmp_state_db,
        config=_config(tmp_artifact_dir, tmp_path / "db"),
        eligibility=BuiltinEligibilityEvaluator(),
        transport=FixtureDrivenTransport(_TRANSPORT),
        persona=ALFAppointmentSetterPersona(),
        crm=MockWriteBackAdapter(tmp_state_db),
        conversation_fixture=None,
        transport_fixture_id=fixture_id,
        clock=FrozenClock(datetime(2026, 5, 19, 19, 0, 0, tzinfo=UTC)),
    )
    assert report.final_disposition is expected_disposition

    writeback = json.loads((report.artifact_dir / "writeback.json").read_text(encoding="utf-8"))
    activity = writeback["phone_call_activity"]

    # Primary assertion (the audit anchor): the Phone Call activity's STRUCTURED
    # `final_disposition` field is the terminal-event disposition, never a connected-
    # conversation outcome. A false connected-call activity would surface here as an
    # `interested_*` / `needs_human_review` / etc. disposition regardless of how the
    # free-text summary happened to be phrased.
    assert activity["final_disposition"] == expected_disposition.value
    _CONNECTED_DISPOSITIONS = {
        "interested_callback_requested",
        "interested_email_captured",
        "needs_human_review",
        "not_interested",
        "call_back_later",
        "do_not_call",
        "wrong_number",
    }
    assert activity["final_disposition"] not in _CONNECTED_DISPOSITIONS, (
        f"no_answer/voicemail/failed activity claims a connected disposition: "
        f"{activity['final_disposition']}"
    )

    # Belt-and-suspenders: the human-readable summary also must not leak connected-flow
    # phrasing into a no_answer / voicemail / failed activity.
    summary = activity["summary"].lower()
    forbidden_phrases = ("interested_callback", "interested_email", "callback requested")
    for phrase in forbidden_phrases:
        assert phrase not in summary, f"summary leaks connected-flow phrasing: {summary}"
