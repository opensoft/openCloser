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

import json
from pathlib import Path

import pytest

from opencloser.artifacts.writer import write_session_artifacts
from opencloser.models import RedactionPolicyConfig
from opencloser.redaction.layer import DEFAULT_REPLACEMENT, RedactionLayer
from tests.fixtures.artifact_inputs import make_artifact_inputs

pytestmark = pytest.mark.integration

_SUMMARY = "Interested; callback requested for Thursday 14:00."
_TRANSCRIPT_WITH_PII = (
    "[persona] Could I confirm the best callback number?\n"
    "[contact] Yes, it's 555-123-4567 and email alice@example.com.\n"
    "[persona] Thank you — I'll have someone follow up.\n"
)


def _inputs(session_id: str) -> dict[str, object]:
    return make_artifact_inputs(session_id, transcript_text=_TRANSCRIPT_WITH_PII, summary=_SUMMARY)


def test_us6_redacted_token_written_to_transcript(tmp_artifact_dir: Path) -> None:
    """Spec §Story 6 acceptance: transcript file contains ``[REDACTED]`` and not the
    original PII when the default regex policy is in effect."""
    session_id = "ses_us6"
    layer = RedactionLayer.from_config(RedactionPolicyConfig())  # regex / full
    paths = write_session_artifacts(
        artifact_root=tmp_artifact_dir,
        session_id=session_id,
        redaction_layer=layer,
        **_inputs(session_id),
    )
    assert paths.transcript is not None and paths.transcript.exists()
    content = paths.transcript.read_text(encoding="utf-8")
    assert "555-123-4567" not in content
    assert "alice@example.com" not in content
    assert DEFAULT_REPLACEMENT in content
    sr = json.loads(paths.session_result.read_text(encoding="utf-8"))
    assert sr["summary"] == _SUMMARY
    assert sr["transcript_pointer"] == "transcript.txt"


def test_us6_summary_only_retention_writes_no_transcript(tmp_artifact_dir: Path) -> None:
    """Spec §Story 6 acceptance: summary-only retention writes NO transcript file;
    the session-result summary remains and the transcript pointer is null so no
    artifact reader can be led to a file that does not exist (FR-030)."""
    session_id = "ses_us6_sum"
    layer = RedactionLayer.from_config(
        RedactionPolicyConfig(policy="regex", retention="summary-only")
    )
    paths = write_session_artifacts(
        artifact_root=tmp_artifact_dir,
        session_id=session_id,
        redaction_layer=layer,
        **_inputs(session_id),
    )
    assert paths.transcript is None
    assert not (tmp_artifact_dir / session_id / "transcript.txt").exists()
    sr = json.loads(paths.session_result.read_text(encoding="utf-8"))
    assert sr["summary"] == _SUMMARY
    assert sr["transcript_pointer"] is None


def test_us6_noop_policy_preserves_slice1_contract(tmp_artifact_dir: Path) -> None:
    """FR-029: explicit no-op policy preserves the unredacted transcript contract."""
    session_id = "ses_us6_noop"
    layer = RedactionLayer.from_config(RedactionPolicyConfig(policy="noop"))
    paths = write_session_artifacts(
        artifact_root=tmp_artifact_dir,
        session_id=session_id,
        redaction_layer=layer,
        **_inputs(session_id),
    )
    assert paths.transcript is not None and paths.transcript.exists()
    content = paths.transcript.read_text(encoding="utf-8")
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
