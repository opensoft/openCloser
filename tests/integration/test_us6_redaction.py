"""US6 Story 6 — Transcript redaction layer (P3, SC-009).

Independent Test (per spec §Story 6):

  Run a scripted conversation whose transcript contains a redaction-policy match;
  confirm the written artifact stores ``[REDACTED]``. Re-run with summary-only
  retention; confirm no transcript file is written while the session-result
  summary remains.

Also covers FR-029 (no-op policy preserves the Slice 1 artifact contract) and
the readiness-failure surface for a malformed redaction policy.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from opencloser.artifacts.writer import write_session_artifacts
from opencloser.models import (
    CallableStatus,
    Disposition,
    ExportedEligibilityDecision,
    NormalizedResult,
    PhoneCallActivityPayload,
    QueueStatusUpdatePayload,
    RedactionPolicyConfig,
    TaskPayload,
    WriteBack,
)
from opencloser.redaction.layer import DEFAULT_REPLACEMENT, RedactionLayer

pytestmark = pytest.mark.integration

_T = "2026-05-19T17:00:00.000Z"

_TRANSCRIPT_WITH_PII = (
    "[persona] Could I confirm the best callback number?\n"
    "[contact] Yes, it's 555-123-4567 and email alice@example.com.\n"
    "[persona] Thank you — I'll have someone follow up.\n"
)
_SUMMARY = "Interested; callback requested for Thursday 14:00."


def _make_inputs(session_id: str = "ses_us6") -> dict[str, object]:
    nr = NormalizedResult(
        session_id=session_id,
        queue_item_id="q1",
        mock_provider_call_id="call_x",
        persona_version="alf-appointment-setter@0.1.0",
        final_disposition=Disposition.INTERESTED_CALLBACK_REQUESTED,
        summary=_SUMMARY,
        transcript_pointer="transcript.txt",
        callback_requested=True,
        preferred_callback_window="Thursday 14:00",
        captured_email=None,
        started_at=_T,
        ended_at=_T,
    )
    activity = PhoneCallActivityPayload(
        session_id=session_id,
        queue_item_id="q1",
        mock_provider_call_id="call_x",
        persona_version="alf-appointment-setter@0.1.0",
        final_disposition=Disposition.INTERESTED_CALLBACK_REQUESTED,
        summary=_SUMMARY,
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
        captured_email=None,
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
        "transcript_text": _TRANSCRIPT_WITH_PII,
    }


def test_us6_redacted_token_written_to_transcript(tmp_artifact_dir: Path) -> None:
    """Spec §Story 6 acceptance: transcript file contains ``[REDACTED]`` and not the
    original PII when the default regex policy is in effect."""
    layer = RedactionLayer.from_config(RedactionPolicyConfig())  # regex / full
    paths = write_session_artifacts(
        artifact_root=tmp_artifact_dir,
        session_id="ses_us6",
        redaction_layer=layer,
        **_make_inputs(),
    )
    assert paths.transcript is not None and paths.transcript.exists()
    content = paths.transcript.read_text(encoding="utf-8")
    assert "555-123-4567" not in content
    assert "alice@example.com" not in content
    assert DEFAULT_REPLACEMENT in content
    # The Slice 1 contract (summary + transcript pointer) is unchanged.
    sr = paths.session_result.read_text(encoding="utf-8")
    assert f'"summary": "{_SUMMARY}"' in sr
    assert '"transcript_pointer": "transcript.txt"' in sr


def test_us6_summary_only_retention_writes_no_transcript(tmp_artifact_dir: Path) -> None:
    """Spec §Story 6 acceptance: summary-only retention writes NO transcript file;
    the session-result summary remains."""
    layer = RedactionLayer.from_config(
        RedactionPolicyConfig(policy="regex", retention="summary-only")
    )
    paths = write_session_artifacts(
        artifact_root=tmp_artifact_dir,
        session_id="ses_us6_sum",
        redaction_layer=layer,
        **_make_inputs("ses_us6_sum"),
    )
    assert paths.transcript is None
    assert not (tmp_artifact_dir / "ses_us6_sum" / "transcript.txt").exists()
    sr = paths.session_result.read_text(encoding="utf-8")
    # Summary preserved; transcript pointer field still present (Slice 1 contract).
    assert f'"summary": "{_SUMMARY}"' in sr


def test_us6_noop_policy_preserves_slice1_contract(tmp_artifact_dir: Path) -> None:
    """FR-029: explicit no-op policy preserves the unredacted transcript contract."""
    layer = RedactionLayer.from_config(RedactionPolicyConfig(policy="noop"))
    paths = write_session_artifacts(
        artifact_root=tmp_artifact_dir,
        session_id="ses_us6_noop",
        redaction_layer=layer,
        **_make_inputs("ses_us6_noop"),
    )
    assert paths.transcript is not None and paths.transcript.exists()
    content = paths.transcript.read_text(encoding="utf-8")
    # PII stays exactly as supplied — no redaction was applied.
    assert "555-123-4567" in content
    assert "alice@example.com" in content
    assert DEFAULT_REPLACEMENT not in content


def test_us6_malformed_policy_fails_readiness() -> None:
    """SC-009 / FR-028 readiness gate: a malformed regex in ``[redaction] patterns``
    fails layer construction — the orchestrator surfaces this as a readiness failure
    before any session is run."""
    bad_cfg = RedactionPolicyConfig(policy="regex", patterns=[r"(?P<bad"])
    with pytest.raises(ValueError, match="Invalid redaction regex"):
        RedactionLayer.from_config(bad_cfg)
