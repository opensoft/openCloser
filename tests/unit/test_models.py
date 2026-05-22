"""Unit tests for Pydantic v2 entity models (FR-002 / FR-013 / FR-014 / FR-028-FR-030 / FR-034)."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from opencloser.models import (
    CallableStatus,
    CallWindowConfig,
    Disposition,
    EventType,
    Extraction,
    HumanReviewReason,
    IntentClassification,
    MockCallEvent,
    NormalizedResult,
    QueueItem,
    QueueStatusUpdatePayload,
    RoleConfidence,
    Session,
    SessionState,
    TaskPayload,
    WriteBack,
)

pytestmark = pytest.mark.module("models")

_T = "2026-05-19T17:00:00.000Z"


# -- Config validation --------------------------------------------------------


def test_call_window_config_rejects_out_of_range_time() -> None:
    """A syntactically valid HH:MM that is out of range (e.g. "99:99") fails config
    validation, so a bad call_window crashes neither config load nor eligibility."""
    CallWindowConfig(start="09:00", end="20:00")  # valid — no raise
    with pytest.raises(ValidationError, match="not a valid HH:MM time"):
        CallWindowConfig(start="99:99", end="20:00")
    with pytest.raises(ValidationError, match="not a valid HH:MM time"):
        CallWindowConfig(start="09:00", end="08:60")


def test_mock_call_event_rejects_bad_payload_value_types() -> None:
    """Q15 — a payload value with the wrong type or an unknown enum value is rejected."""
    with pytest.raises(ValidationError, match="voicemail_length_seconds"):
        MockCallEvent(
            session_id="s",
            event_id="e",
            event_type=EventType.VOICEMAIL,
            received_at=_T,
            payload={"voicemail_length_seconds": "abc"},
        )
    with pytest.raises(ValidationError, match="failure_reason"):
        MockCallEvent(
            session_id="s",
            event_id="e",
            event_type=EventType.FAILED,
            received_at=_T,
            payload={"failure_reason": "bogus"},
        )


# -- Round-trip ---------------------------------------------------------------


def test_queue_item_round_trip() -> None:
    item = QueueItem(
        queue_item_id="q1",
        facility_name="Sunset Ridge",
        phone_number="+15555550100",
        timezone="America/Los_Angeles",
        attempt_count=0,
        callable_status=CallableStatus.READY,
    )
    payload = item.model_dump(mode="json")
    restored = QueueItem.model_validate_json(json.dumps(payload))
    assert restored == item


def test_session_round_trip() -> None:
    session = Session(
        session_id="ses_1",
        queue_item_id="q1",
        state=SessionState.FINALIZED,
        final_disposition=Disposition.INTERESTED_CALLBACK_REQUESTED,
        started_at=_T,
        ended_at=_T,
    )
    restored = Session.model_validate_json(session.model_dump_json())
    assert restored == session


def test_normalized_result_round_trip() -> None:
    nr = NormalizedResult(
        session_id="ses_1",
        queue_item_id="q1",
        final_disposition=Disposition.INTERESTED_CALLBACK_REQUESTED,
        summary="ok",
        callback_requested=True,
        preferred_callback_window="Thursday 14:00",
        started_at=_T,
        ended_at=_T,
    )
    out = nr.model_dump(mode="json")
    assert out["schema_version"] == "slice1-v1"
    assert NormalizedResult.model_validate(out) == nr


# -- Validators --------------------------------------------------------------


def test_normalized_result_email_mutual_exclusion() -> None:
    with pytest.raises(ValidationError):
        NormalizedResult(
            session_id="ses_1",
            queue_item_id="q1",
            final_disposition=Disposition.NEEDS_HUMAN_REVIEW,
            captured_email="ok@example.com",
            captured_email_unverified="ok@example.com",
            started_at=_T,
            ended_at=_T,
        )


def test_extraction_email_mutual_exclusion() -> None:
    with pytest.raises(ValidationError):
        Extraction(
            captured_email="ok@example.com",
            captured_email_unverified="ok@example.com",
            role_confidence=RoleConfidence.CONFIDENT_DECISION_MAKER,
            intent_classification=IntentClassification.INTERESTED,
        )


def test_task_payload_review_requires_reason() -> None:
    with pytest.raises(ValidationError):
        TaskPayload(
            task_id="task_1",
            session_id="ses_1",
            queue_item_id="q1",
            task_kind="review",
            subject="needs review",
            reason_code=None,
            persona_version="alf-appointment-setter@0.1.0",
            created_at=_T,
        )


def test_task_payload_callback_with_email_and_window() -> None:
    payload = TaskPayload(
        task_id="task_2",
        session_id="ses_1",
        queue_item_id="q1",
        task_kind="callback",
        subject="Callback Thursday 14:00",
        preferred_callback_window="Thursday 14:00",
        captured_email="ok@example.com",
        persona_version="alf-appointment-setter@0.1.0",
        created_at=_T,
    )
    assert payload.reason_code is None
    assert payload.assigned_to is None


def test_task_payload_callback_rejects_reason_code() -> None:
    """crm M1 / FR-030: `reason_code` is null for callback tasks."""
    with pytest.raises(ValidationError):
        TaskPayload(
            task_id="task_3",
            session_id="ses_1",
            queue_item_id="q1",
            task_kind="callback",
            subject="Callback Thursday 14:00",
            reason_code=HumanReviewReason.UNCERTAIN_ROLE,
            persona_version="alf-appointment-setter@0.1.0",
            created_at=_T,
        )


def test_task_payload_review_rejects_captured_email() -> None:
    """crm M2 / FR-030: `captured_email` is a callback-task field, never on a review task."""
    with pytest.raises(ValidationError):
        TaskPayload(
            task_id="task_4",
            session_id="ses_1",
            queue_item_id="q1",
            task_kind="review",
            subject="Review uncertain intent",
            reason_code=HumanReviewReason.UNCERTAIN_INTENT,
            captured_email="ok@example.com",
            persona_version="alf-appointment-setter@0.1.0",
            created_at=_T,
        )


# -- Timestamp format --------------------------------------------------------


def test_timestamp_pattern_rejects_non_utc_ms() -> None:
    with pytest.raises(ValidationError):
        Session(
            session_id="ses_1",
            queue_item_id="q1",
            state=SessionState.CREATED,
            started_at="2026-05-19 17:00:00",  # not ISO 8601 with Z
        )


def test_summary_max_length() -> None:
    with pytest.raises(ValidationError):
        NormalizedResult(
            session_id="ses_1",
            queue_item_id="q1",
            final_disposition=Disposition.INTERESTED_CALLBACK_REQUESTED,
            summary="x" * 201,
            started_at=_T,
            ended_at=_T,
        )


# -- Enum coverage -----------------------------------------------------------


def test_disposition_enum_has_eleven_values() -> None:
    assert len(list(Disposition)) == 11
    assert "blocked" in {d.value for d in Disposition}


def test_human_review_reason_has_nine_values() -> None:
    assert len(list(HumanReviewReason)) == 9


def test_event_type_has_six_values() -> None:
    assert len(list(EventType)) == 6


# -- WriteBack shape ---------------------------------------------------------


def test_writeback_requires_queue_status() -> None:
    with pytest.raises(ValidationError):
        WriteBack(session_id="ses_1")  # missing queue_status_update


def test_writeback_blocked_session_no_phone_call() -> None:
    wb = WriteBack(
        session_id="ses_1",
        queue_status_update=QueueStatusUpdatePayload(
            session_id="ses_1",
            queue_item_id="q1",
            previous_status=CallableStatus.READY,
            new_status=CallableStatus.READY,
            transition_reason="blocked_by_eligibility: d",
            transition_at=_T,
        ),
    )
    assert wb.phone_call_activity is None
    assert wb.task is None
