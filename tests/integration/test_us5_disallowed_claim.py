"""T059 — US5 integration: disallowed-claim escalation (FR-015).

US5 acceptance scenario #2: when the live model attempts to emit a claim outside
the allowed-claim categories (e.g. an exact monthly price), the persona MUST
escalate ``needs_human_review`` with the matching enumerated reason and the
conversation MUST end safely (no further live-model authority over the outcome).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from opencloser.models import Disposition, HumanReviewReason
from opencloser.persona.alf_appointment_setter import CANONICAL_DISCLOSURE
from tests.fixtures.pipecat import FakeRealtimeAIProvider, FakeTranscriptSegment
from tests.fixtures.us5_runtime import make_session_context, run_runtime

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_live_model_exact_price_escalates(tmp_path: Path) -> None:
    provider = FakeRealtimeAIProvider(
        scripted_frames=[
            FakeTranscriptSegment(text=CANONICAL_DISCLOSURE, speaker="persona"),
            FakeTranscriptSegment(
                text="The monthly cost for memory care at Sunset Ridge is exactly $4,852.",
                speaker="persona",
            ),
        ]
    )
    output, _ = await run_runtime(provider, make_session_context(tmp_path))

    assert output.final_disposition is Disposition.NEEDS_HUMAN_REVIEW
    assert output.human_review_reason in {
        HumanReviewReason.OUTSIDE_ALLOWED_CLAIMS,
        HumanReviewReason.NON_CLINICAL_TOPIC_ESCALATION,
    }


@pytest.mark.asyncio
async def test_live_model_clinical_recommendation_escalates(tmp_path: Path) -> None:
    """A live-model clinical recommendation (out-of-scope) escalates the
    non-clinical-topic reason and ends safely."""
    provider = FakeRealtimeAIProvider(
        scripted_frames=[
            FakeTranscriptSegment(text=CANONICAL_DISCLOSURE, speaker="persona"),
            FakeTranscriptSegment(
                text="You should take a higher dose of that medication for the fall risk.",
                speaker="persona",
            ),
        ]
    )
    output, _ = await run_runtime(provider, make_session_context(tmp_path))

    assert output.final_disposition is Disposition.NEEDS_HUMAN_REVIEW
    assert output.human_review_reason in {
        HumanReviewReason.OUTSIDE_ALLOWED_CLAIMS,
        HumanReviewReason.NON_CLINICAL_TOPIC_ESCALATION,
    }
