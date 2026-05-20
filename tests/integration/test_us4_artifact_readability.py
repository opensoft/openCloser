"""US4 Story 4 — Inspect normalized results and follow-up task payloads (P3).

Independent Test: for every Slice 1 disposition, the exported artifacts contain the
right FR-014 fields, the right FR-031 write-back shape, and the right FR-032 new_status.
Per Clarifications Round 2 Q5, the captured-email-AND-callback case carries both
`preferred_callback_window` and `captured_email` on the callback task payload.
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
_CONV_DIR = _REPO / "tests/fixtures/conversations"
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


def _load_conv(name: str) -> ConversationFixture:
    raw = json.loads((_CONV_DIR / f"{name}.json").read_text(encoding="utf-8"))
    return ConversationFixture(
        fixture_id=raw["fixture_id"],
        expected_disposition=raw["expected_disposition"],
        queue_item_ref=raw["queue_item_ref"],
        turns=[ConversationTurn(role=t["role"], text=t["text"]) for t in raw["turns"]],
        expected_extraction=raw["expected_extraction"],
    )


def _run(
    conv_name: str,
    tmp_state_db: sqlite3.Connection,
    tmp_artifact_dir: Path,
    tmp_path: Path,
):
    store.insert_queue_item(
        tmp_state_db, QueueItem.model_validate_json(_QUEUE.read_text(encoding="utf-8"))
    )
    return process_one_queue_item(
        "alf-prospect-001",
        conn=tmp_state_db,
        config=_config(tmp_artifact_dir, tmp_path / "db"),
        eligibility=BuiltinEligibilityEvaluator(),
        transport=FixtureDrivenTransport(_TRANSPORT),
        persona=ALFAppointmentSetterPersona(),
        conversation_fixture=_load_conv(conv_name),
        transport_fixture_id="connected",
        clock=FrozenClock(datetime(2026, 5, 19, 19, 0, 0, tzinfo=UTC)),
    )


# Each row: (conv fixture, expected disposition, expects_task_kind, expects_new_status).
_CASES = [
    ("interested_callback_requested", Disposition.INTERESTED_CALLBACK_REQUESTED, "callback", "ready"),
    ("interested_email_captured", Disposition.INTERESTED_EMAIL_CAPTURED, "callback", "completed"),
    ("interested_email_and_callback", Disposition.INTERESTED_CALLBACK_REQUESTED, "callback", "ready"),
    ("needs_human_review_uncertain_role", Disposition.NEEDS_HUMAN_REVIEW, "review", "blocked"),
    ("needs_human_review_email_invalid", Disposition.NEEDS_HUMAN_REVIEW, "review", "blocked"),
    ("do_not_call_mid_call", Disposition.DO_NOT_CALL, None, "dnc"),
    ("wrong_number", Disposition.WRONG_NUMBER, None, "blocked"),
    ("not_interested", Disposition.NOT_INTERESTED, None, "completed"),
    ("call_back_later", Disposition.CALL_BACK_LATER, "callback", "ready"),
    ("script_truncated", Disposition.NEEDS_HUMAN_REVIEW, "review", "blocked"),
]


@pytest.mark.parametrize("conv_name,disposition,task_kind,new_status", _CASES)
def test_us4_per_disposition_shape_and_readability(
    tmp_state_db: sqlite3.Connection,
    tmp_artifact_dir: Path,
    tmp_path: Path,
    conv_name: str,
    disposition: Disposition,
    task_kind: str | None,
    new_status: str,
) -> None:
    report = _run(conv_name, tmp_state_db, tmp_artifact_dir, tmp_path)
    assert report.final_disposition is disposition

    # FR-014: session-result.json carries the required fields.
    session_result = json.loads((report.artifact_dir / "session-result.json").read_text(encoding="utf-8"))
    assert session_result["schema_version"] == "slice1-v1"
    assert session_result["final_disposition"] == disposition.value
    assert session_result["session_id"] == report.session_id
    assert session_result["queue_item_id"] == "alf-prospect-001"
    if disposition is Disposition.NEEDS_HUMAN_REVIEW:
        assert session_result["human_review_reason"] is not None

    # FR-031: per-disposition write-back shape.
    writeback = json.loads((report.artifact_dir / "writeback.json").read_text(encoding="utf-8"))
    # All connected dispositions emit a phone_call_activity (FR-031 only excludes `blocked`).
    assert writeback["phone_call_activity"] is not None, "FR-031: non-blocked emits activity"
    if task_kind is None:
        assert writeback["task"] is None, f"FR-018 / FR-031: {disposition} MUST NOT emit a task"
    else:
        assert writeback["task"] is not None
        assert writeback["task"]["task_kind"] == task_kind

    # FR-032: per-disposition new_status.
    assert writeback["queue_status_update"]["new_status"] == new_status


def test_us4_q5_callback_task_carries_email_and_window(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path, tmp_path: Path
) -> None:
    """Q5 Clarification: verified email + callback → both fields populated on callback task."""
    report = _run("interested_email_and_callback", tmp_state_db, tmp_artifact_dir, tmp_path)
    assert report.final_disposition is Disposition.INTERESTED_CALLBACK_REQUESTED
    task = json.loads((report.artifact_dir / "task.json").read_text(encoding="utf-8"))
    assert task["task_kind"] == "callback"
    assert task["preferred_callback_window"] is not None
    assert task["captured_email"] == "owner@sunset.example.com"


def test_us4_dnc_mid_call_persists_dnc_signal(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path, tmp_path: Path
) -> None:
    """Edge Case 'DNC stated mid-conversation' — queue record's dnc_flag and callable_status transition to dnc."""
    report = _run("do_not_call_mid_call", tmp_state_db, tmp_artifact_dir, tmp_path)
    assert report.final_disposition is Disposition.DO_NOT_CALL
    qi = store.get_queue_item(tmp_state_db, "alf-prospect-001")
    assert qi is not None
    assert qi.callable_status.value == "dnc"
    assert qi.dnc_flag is True


# FR-035 reason codes reachable through the integration path. The first 3 rows close
# the H7 coverage gap (`non_clinical_topic_escalation`, `ambiguous_dnc`,
# `uncertain_intent` were previously untested anywhere); the 3 existing fixtures are
# pinned alongside so an append-only change to the FR-035 enum is caught here too.
_FR035_CASES = [
    ("non_clinical_topic_escalation", "non_clinical_topic_escalation"),
    ("ambiguous_dnc", "ambiguous_dnc"),
    ("uncertain_intent", "uncertain_intent"),
    ("needs_human_review_uncertain_role", "uncertain_role"),
    ("needs_human_review_email_invalid", "captured_email_invalid_no_callback"),
    ("script_truncated", "script_truncated"),
]


@pytest.mark.parametrize("conv_name,expected_reason", _FR035_CASES)
def test_us4_fr035_reason_code_recorded(
    tmp_state_db: sqlite3.Connection,
    tmp_artifact_dir: Path,
    tmp_path: Path,
    conv_name: str,
    expected_reason: str,
) -> None:
    """FR-035: each integration-reachable `human_review_reason` code is recorded verbatim
    on the exported session result AND carried as the review task's `reason_code`."""
    report = _run(conv_name, tmp_state_db, tmp_artifact_dir, tmp_path)
    assert report.final_disposition is Disposition.NEEDS_HUMAN_REVIEW

    # FR-014: the specific reason code (not just non-null) is on the session result.
    session_result = json.loads(
        (report.artifact_dir / "session-result.json").read_text(encoding="utf-8")
    )
    assert session_result["human_review_reason"] == expected_reason

    # FR-030: the review task payload carries the same reason code.
    task = json.loads((report.artifact_dir / "task.json").read_text(encoding="utf-8"))
    assert task["task_kind"] == "review"
    assert task["reason_code"] == expected_reason
