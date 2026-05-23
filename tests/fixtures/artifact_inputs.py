"""Shared builder for ``write_session_artifacts`` inputs.

Used by the artifact-writer unit tests and the US6 redaction unit + integration
tests so that the fixture shape lives in one place. Keep this aligned with
``contracts/redaction-layer.md`` and the Slice 1 artifact contract.
"""

from __future__ import annotations

from opencloser.models import (
    CallableStatus,
    Disposition,
    ExportedEligibilityDecision,
    NormalizedResult,
    PhoneCallActivityPayload,
    QueueStatusUpdatePayload,
    TaskPayload,
    WriteBack,
)

_T = "2026-05-19T17:00:00.000Z"

DEFAULT_TRANSCRIPT = "[persona] Hi, this is an AI assistant.\n[contact] Sure.\n"


def make_artifact_inputs(
    session_id: str = "ses_1",
    *,
    transcript_text: str | None = DEFAULT_TRANSCRIPT,
    summary: str = "Decision-maker confirmed interested; callback requested Thursday 14:00.",
    captured_email: str | None = "ok@example.com",
) -> dict[str, object]:
    """Build the keyword inputs accepted by ``write_session_artifacts``.

    Every payload is keyed off ``session_id`` so the directory name and the
    JSON-payload ``session_id`` fields stay coherent.
    """
    nr = NormalizedResult(
        session_id=session_id,
        queue_item_id="q1",
        mock_provider_call_id="call_x",
        persona_version="alf-appointment-setter@0.1.0",
        final_disposition=Disposition.INTERESTED_CALLBACK_REQUESTED,
        summary=summary,
        # Mirror the orchestrator: only advertise a transcript file when one will
        # actually be written. Keeps the fixture from generating dangling pointers.
        transcript_pointer="transcript.txt" if transcript_text is not None else None,
        callback_requested=True,
        preferred_callback_window="Thursday 14:00",
        captured_email=captured_email,
        started_at=_T,
        ended_at=_T,
    )
    activity = PhoneCallActivityPayload(
        session_id=session_id,
        queue_item_id="q1",
        mock_provider_call_id="call_x",
        persona_version="alf-appointment-setter@0.1.0",
        final_disposition=Disposition.INTERESTED_CALLBACK_REQUESTED,
        summary=summary,
        started_at=_T,
        ended_at=_T,
    )
    status = QueueStatusUpdatePayload(
        session_id=session_id,
        queue_item_id="q1",
        previous_status=CallableStatus.READY,
        new_status=CallableStatus.READY,
        transition_reason="interested_callback_requested",
        transition_at=_T,
    )
    task = TaskPayload(
        task_id="task_1",
        session_id=session_id,
        queue_item_id="q1",
        task_kind="callback",
        subject="Callback Thursday 14:00",
        preferred_callback_window="Thursday 14:00",
        captured_email=captured_email,
        persona_version="alf-appointment-setter@0.1.0",
        created_at=_T,
    )
    writeback = WriteBack(
        session_id=session_id,
        phone_call_activity=activity,
        queue_status_update=status,
        task=task,
    )
    eligibility = ExportedEligibilityDecision(
        decision_id="dec_1",
        queue_item_id="q1",
        session_id=session_id,
        decided_at=_T,
        outcome="allow",
        rules={"a": True, "b": True, "c": True, "d": True, "e": True, "f": True},
    )
    return {
        "normalized_result": nr,
        "writeback": writeback,
        "eligibility_decision": eligibility,
        "task": task,
        "transcript_text": transcript_text,
    }
