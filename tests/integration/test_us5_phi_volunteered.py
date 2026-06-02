"""T063 — US5 integration: caller-volunteered PHI (Round 2 Q11).

When a caller volunteers PHI despite the persona refusing to ask for it, the
runtime MUST:

- escalate ``needs_human_review`` with reason ``phi_collection_risk``;
- run the redaction layer's PHI tag-and-redact pass over the in-flight
  transcript / summary / shadow transcript / shadow discrepancy buffers BEFORE
  any artifact write — so the PHI substring never reaches the summary or any
  persisted artifact.

Shadow-disabled variant (contract Required-Behavior #4 / CHK123): with shadow
STT disabled only the transcript + summary exist; the pass redacts those two and
the absent shadow artifacts are NOT a failure.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from opencloser.models import Disposition, HumanReviewReason
from opencloser.persona.alf_appointment_setter import CANONICAL_DISCLOSURE
from tests.fixtures.pipecat import FakeRealtimeAIProvider, FakeTranscriptSegment
from tests.fixtures.us5_runtime import make_session_context, run_runtime

pytestmark = pytest.mark.integration

_PHI_UTTERANCE = "My mother takes 10mg of methotrexate weekly for rheumatoid arthritis."


@pytest.mark.asyncio
async def test_phi_escalates_and_redacts_shadow_enabled(tmp_path: Path) -> None:
    provider = FakeRealtimeAIProvider(
        scripted_frames=[
            FakeTranscriptSegment(text=CANONICAL_DISCLOSURE, speaker="persona"),
            FakeTranscriptSegment(text=_PHI_UTTERANCE, speaker="caller"),
        ]
    )
    output, runtime = await run_runtime(
        provider, make_session_context(tmp_path), shadow_stt_enabled=True
    )

    assert output.final_disposition is Disposition.NEEDS_HUMAN_REVIEW
    assert output.human_review_reason is HumanReviewReason.PHI_COLLECTION_RISK
    assert runtime.phi_volunteered is True
    assert "methotrexate" not in (output.summary or "").lower()

    # All four artifact buffers were redacted before write (shadow enabled).
    redacted = runtime.redacted_artifacts
    assert set(redacted) >= {
        "transcript",
        "summary",
        "shadow_transcript",
        "shadow_discrepancy_records",
    }
    for value in redacted.values():
        texts = value if isinstance(value, list) else [value]
        for text in texts:
            assert "methotrexate" not in text.lower()


@pytest.mark.asyncio
async def test_phi_redacts_shadow_disabled_two_artifacts(tmp_path: Path) -> None:
    """Shadow disabled: only transcript + summary are produced; the absent shadow
    artifacts are not a failure and the two produced artifacts are still
    redacted."""
    provider = FakeRealtimeAIProvider(
        scripted_frames=[
            FakeTranscriptSegment(text=CANONICAL_DISCLOSURE, speaker="persona"),
            FakeTranscriptSegment(text=_PHI_UTTERANCE, speaker="caller"),
        ]
    )
    output, runtime = await run_runtime(
        provider, make_session_context(tmp_path), shadow_stt_enabled=False
    )

    assert output.human_review_reason is HumanReviewReason.PHI_COLLECTION_RISK
    assert "methotrexate" not in (output.summary or "").lower()

    redacted = runtime.redacted_artifacts
    assert "transcript" in redacted
    assert "summary" in redacted
    # Shadow transcript is absent (shadow disabled) and that is not a failure.
    assert "shadow_transcript" not in redacted
    assert redacted.get("shadow_discrepancy_records") == []
    for key in ("transcript", "summary"):
        assert "methotrexate" not in str(redacted[key]).lower()
