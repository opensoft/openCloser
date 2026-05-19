"""Unit tests for the artifact writer (FR-023 + SC-005 deterministic JSON)."""

from __future__ import annotations

from pathlib import Path

import pytest

from opencloser.artifacts.writer import write_session_artifacts
from opencloser.models import (
    CallableStatus,
    ConflictingEventAuditRecord,
    Disposition,
    EventType,
    ExportedEligibilityDecision,
    NormalizedResult,
    PhoneCallActivityPayload,
    QueueStatusUpdatePayload,
    TaskPayload,
    WriteBack,
)

pytestmark = pytest.mark.module("artifacts")

_T = "2026-05-19T17:00:00.000Z"


def _make_inputs(session_id: str = "ses_1") -> dict[str, object]:
    nr = NormalizedResult(
        session_id=session_id,
        queue_item_id="q1",
        mock_provider_call_id="call_x",
        persona_version="alf-appointment-setter@0.1.0",
        final_disposition=Disposition.INTERESTED_CALLBACK_REQUESTED,
        summary="Decision-maker confirmed interested; callback requested Thursday 14:00.",
        transcript_pointer="transcript.txt",
        callback_requested=True,
        preferred_callback_window="Thursday 14:00",
        captured_email="ok@example.com",
        started_at=_T,
        ended_at=_T,
    )
    activity = PhoneCallActivityPayload(
        session_id=session_id,
        queue_item_id="q1",
        mock_provider_call_id="call_x",
        persona_version="alf-appointment-setter@0.1.0",
        final_disposition=Disposition.INTERESTED_CALLBACK_REQUESTED,
        summary=nr.summary or "",
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
        captured_email="ok@example.com",
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
        "transcript_text": "[persona] Hi, this is an AI assistant.\n[contact] Sure.\n",
    }


def test_artifacts_written_to_session_dir(tmp_artifact_dir: Path) -> None:
    paths = write_session_artifacts(artifact_root=tmp_artifact_dir, session_id="ses_1", **_make_inputs())
    assert paths.session_dir == tmp_artifact_dir / "ses_1"
    assert paths.session_result.exists()
    assert paths.writeback.exists()
    assert paths.task is not None and paths.task.exists()
    assert paths.transcript is not None and paths.transcript.exists()
    assert paths.eligibility_decision.exists()
    assert paths.conflicting_events is None  # not emitted unless there were rejections


def test_artifacts_are_byte_identical_across_runs(tmp_artifact_dir: Path) -> None:
    """SC-005: rerunning the same fixture MUST produce byte-identical artifacts."""
    inputs = _make_inputs()
    paths_a = write_session_artifacts(artifact_root=tmp_artifact_dir, session_id="ses_1", **inputs)
    snapshot_a = {p.name: p.read_bytes() for p in tmp_artifact_dir.rglob("*") if p.is_file()}

    # Re-run with the same inputs — same session_id, same artifacts dir.
    paths_b = write_session_artifacts(artifact_root=tmp_artifact_dir, session_id="ses_1", **inputs)
    snapshot_b = {p.name: p.read_bytes() for p in tmp_artifact_dir.rglob("*") if p.is_file()}

    assert paths_a.session_result == paths_b.session_result
    assert snapshot_a == snapshot_b


def test_json_uses_sorted_keys_and_indent(tmp_artifact_dir: Path) -> None:
    write_session_artifacts(artifact_root=tmp_artifact_dir, session_id="ses_1", **_make_inputs())
    content = (tmp_artifact_dir / "ses_1" / "session-result.json").read_text(encoding="utf-8")
    # 2-space indent: every nested line begins with two spaces.
    nested_lines = [ln for ln in content.splitlines() if ln.startswith(" ")]
    assert all(ln.startswith("  ") for ln in nested_lines)
    # sorted keys: schema_version is alphabetically before session_id.
    first_key_index = content.index('"')
    excerpt = content[first_key_index : first_key_index + 200]
    assert '"callback_requested"' in excerpt or '"captured_email"' in excerpt or '"ended_at"' in excerpt


def test_transcript_uses_lf_and_trailing_newline(tmp_artifact_dir: Path) -> None:
    inputs = _make_inputs()
    inputs["transcript_text"] = "[persona] one\n[contact] two"
    write_session_artifacts(artifact_root=tmp_artifact_dir, session_id="ses_1", **inputs)
    transcript = (tmp_artifact_dir / "ses_1" / "transcript.txt").read_bytes()
    assert b"\r\n" not in transcript
    assert transcript.endswith(b"\n")


def test_conflicting_events_artifact_emitted_only_when_present(tmp_artifact_dir: Path) -> None:
    inputs = _make_inputs()
    inputs["conflicting_events"] = [
        ConflictingEventAuditRecord(
            audit_id="audit_1",
            session_id="ses_1",
            event_id="evt_late",
            conflicting_event_type=EventType.FAILED,
            received_at=_T,
            full_event_payload={"failure_reason": "carrier_error"},
            preserved_disposition=Disposition.NO_ANSWER,
        )
    ]
    paths = write_session_artifacts(artifact_root=tmp_artifact_dir, session_id="ses_1", **inputs)
    assert paths.conflicting_events is not None
    assert paths.conflicting_events.exists()


def test_blocked_session_omits_phone_call_activity_and_task(tmp_artifact_dir: Path) -> None:
    """FR-031: blocked session has no phone_call_activity and no task."""
    inputs = _make_inputs()
    blocked_writeback = WriteBack(
        session_id="ses_1",
        phone_call_activity=None,
        queue_status_update=inputs["writeback"].queue_status_update,  # type: ignore[union-attr]
        task=None,
    )
    inputs["writeback"] = blocked_writeback
    inputs["task"] = None
    paths = write_session_artifacts(artifact_root=tmp_artifact_dir, session_id="ses_1", **inputs)
    assert paths.task is None
    writeback_content = paths.writeback.read_text(encoding="utf-8")
    assert '"phone_call_activity": null' in writeback_content
    assert '"task": null' in writeback_content
