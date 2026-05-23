"""Unit tests for the transcript RedactionLayer (FR-028, FR-029, FR-030, SC-009).

Covers the contract in
``specs/002-mock-call-real-crm/contracts/redaction-layer.md`` — default-on regex
policy with ``[REDACTED]`` replacement, no-op policy preserving transcript bytes,
summary-only retention, and readiness failure for a malformed redaction pattern.
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
from opencloser.redaction.layer import (
    DEFAULT_REPLACEMENT,
    NoOpPolicy,
    RedactionLayer,
    RegexRedactionPolicy,
)

pytestmark = pytest.mark.module("redaction")

_T = "2026-05-19T17:00:00.000Z"


# ---------------------------------------------------------------------------
# RedactionLayer construction & policy behavior
# ---------------------------------------------------------------------------


def test_default_layer_redacts_emails_and_phone_numbers() -> None:
    layer = RedactionLayer.default()
    text = "Call me at 555-123-4567 or email me at ok@example.com."
    out = layer.redact(text)
    assert "555-123-4567" not in out
    assert "ok@example.com" not in out
    assert DEFAULT_REPLACEMENT in out
    assert layer.retention_mode() == "full"


@pytest.mark.parametrize(
    "raw,expected_redactions",
    [
        ("Call (555) 123-4567 back.", 1),
        ("Try 555.123.4567 or +1 555 123 4567.", 2),
        ("ping bob@example.org and alice@example.co.uk", 2),
        ("Phone 5551234567 dial-only digits not matched", 0),
    ],
)
def test_regex_policy_match_variants(raw: str, expected_redactions: int) -> None:
    policy = RegexRedactionPolicy.from_patterns()
    out = policy.redact(raw)
    assert out.count(DEFAULT_REPLACEMENT) == expected_redactions


def test_noop_policy_returns_text_unchanged() -> None:
    layer = RedactionLayer(policy=NoOpPolicy(), _retention_mode="full")
    text = "Call me at 555-123-4567 or email ok@example.com."
    assert layer.redact(text) == text
    assert layer.retention_mode() == "full"


def test_from_config_regex_default() -> None:
    cfg = RedactionPolicyConfig()  # policy="regex", retention="full" defaults
    layer = RedactionLayer.from_config(cfg)
    assert layer.retention_mode() == "full"
    assert isinstance(layer.policy, RegexRedactionPolicy)
    assert DEFAULT_REPLACEMENT in layer.redact("555-123-4567")


def test_from_config_noop_explicit() -> None:
    cfg = RedactionPolicyConfig(policy="noop", retention="full")
    layer = RedactionLayer.from_config(cfg)
    assert isinstance(layer.policy, NoOpPolicy)
    assert layer.redact("555-123-4567") == "555-123-4567"


def test_from_config_summary_only_retention() -> None:
    cfg = RedactionPolicyConfig(policy="regex", retention="summary-only")
    layer = RedactionLayer.from_config(cfg)
    assert layer.retention_mode() == "summary-only"


def test_from_config_user_extra_patterns() -> None:
    cfg = RedactionPolicyConfig(policy="regex", patterns=[r"SECRET-\d{4}"])
    layer = RedactionLayer.from_config(cfg)
    out = layer.redact("token SECRET-1234 and phone 555-123-4567")
    assert out.count(DEFAULT_REPLACEMENT) == 2


def test_malformed_redaction_pattern_fails_readiness() -> None:
    """SC-009: a malformed redaction policy fails readiness — surfaced as a ValueError
    raised when the layer is built from config (the orchestrator wraps this as a
    readiness failure)."""
    bad_cfg = RedactionPolicyConfig(policy="regex", patterns=["(unclosed"])
    with pytest.raises(ValueError, match="Invalid redaction regex"):
        RedactionLayer.from_config(bad_cfg)


# ---------------------------------------------------------------------------
# Writer integration — covered together with integration tests below
# ---------------------------------------------------------------------------


def _make_artifact_inputs(session_id: str = "ses_red_1") -> dict[str, object]:
    nr = NormalizedResult(
        session_id=session_id,
        queue_item_id="q1",
        mock_provider_call_id="call_x",
        persona_version="alf-appointment-setter@0.1.0",
        final_disposition=Disposition.INTERESTED_CALLBACK_REQUESTED,
        summary="Decision-maker confirmed interested.",
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
        "transcript_text": (
            "[persona] Hi. Could you confirm your callback number?\n"
            "[contact] Sure, it's 555-123-4567 and email alice@example.com.\n"
        ),
    }


def test_writer_redacts_transcript_under_regex_policy(tmp_artifact_dir: Path) -> None:
    """FR-028: with regex policy + full retention, written transcript contains
    ``[REDACTED]`` and not the original PII."""
    inputs = _make_artifact_inputs()
    layer = RedactionLayer.from_config(RedactionPolicyConfig())  # regex / full defaults
    paths = write_session_artifacts(
        artifact_root=tmp_artifact_dir,
        session_id="ses_red_1",
        redaction_layer=layer,
        **inputs,
    )
    assert paths.transcript is not None and paths.transcript.exists()
    content = paths.transcript.read_text(encoding="utf-8")
    assert "555-123-4567" not in content
    assert "alice@example.com" not in content
    assert DEFAULT_REPLACEMENT in content
    # Session-result still names the transcript pointer (Slice 1 contract preserved).
    assert paths.session_result.exists()
    sr = paths.session_result.read_text(encoding="utf-8")
    assert '"transcript_pointer": "transcript.txt"' in sr


def test_writer_summary_only_retention_omits_transcript(tmp_artifact_dir: Path) -> None:
    """FR-030: summary-only retention writes NO transcript file; the session-result
    summary is still emitted."""
    inputs = _make_artifact_inputs()
    layer = RedactionLayer.from_config(
        RedactionPolicyConfig(policy="regex", retention="summary-only")
    )
    paths = write_session_artifacts(
        artifact_root=tmp_artifact_dir,
        session_id="ses_red_2",
        redaction_layer=layer,
        **inputs,
    )
    assert paths.transcript is None
    assert not (tmp_artifact_dir / "ses_red_2" / "transcript.txt").exists()
    # Session-result still present and still carries the summary.
    sr = paths.session_result.read_text(encoding="utf-8")
    assert '"summary": "Decision-maker confirmed interested."' in sr


def test_writer_noop_policy_preserves_slice1_contract(tmp_artifact_dir: Path) -> None:
    """FR-029: no-op policy + full retention writes the transcript byte-identically
    to passing no layer (preserves the Slice 1 artifact contract)."""
    inputs = _make_artifact_inputs()
    noop_layer = RedactionLayer(policy=NoOpPolicy(), _retention_mode="full")

    # Write with explicit no-op layer.
    write_session_artifacts(
        artifact_root=tmp_artifact_dir / "noop",
        session_id="ses_x",
        redaction_layer=noop_layer,
        **inputs,
    )
    noop_bytes = (tmp_artifact_dir / "noop" / "ses_x" / "transcript.txt").read_bytes()

    # The bytes match exactly what we asked to write (Slice 1 unredacted contract).
    transcript_in = inputs["transcript_text"]
    assert isinstance(transcript_in, str)
    expected = transcript_in if transcript_in.endswith("\n") else transcript_in + "\n"
    assert noop_bytes == expected.encode("utf-8")
