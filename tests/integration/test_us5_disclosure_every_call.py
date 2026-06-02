"""T058 — US5 integration: AI disclosure on every connected call (FR-015).

US5 acceptance scenario #1: the persona's first connected-call utterance MUST
contain the canonical AI-on-behalf-of-Medx disclosure. Per Round 1 Q1 the
obligation holds even when the caller is silent / never explicitly acknowledges
the disclosure — absence of an opt-out is implicit acknowledgment and MUST NOT
escalate ``needs_human_review``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from opencloser.persona.alf_appointment_setter import CANONICAL_DISCLOSURE
from tests.fixtures.pipecat import FakeRealtimeAIProvider, FakeTranscriptSegment
from tests.fixtures.us5_runtime import make_session_context, run_runtime

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_disclosure_present_when_caller_acknowledges(tmp_path: Path) -> None:
    """A connected call where the caller acknowledges still carries the disclosure
    as the first connected-call utterance."""
    provider = FakeRealtimeAIProvider(
        scripted_frames=[
            FakeTranscriptSegment(text=CANONICAL_DISCLOSURE, speaker="persona"),
            FakeTranscriptSegment(text="Sure, what's this about?", speaker="caller"),
        ]
    )
    output, _ = await run_runtime(provider, make_session_context(tmp_path))
    assert output.disclosure_completed is True


@pytest.mark.asyncio
async def test_disclosure_present_when_caller_silent_no_escalation(tmp_path: Path) -> None:
    """Round 1 Q1: caller silence after the disclosure does NOT escalate; the
    disclosure obligation is still satisfied (the persona spoke it first)."""
    provider = FakeRealtimeAIProvider(
        scripted_frames=[
            FakeTranscriptSegment(text=CANONICAL_DISCLOSURE, speaker="persona"),
            FakeTranscriptSegment(text="(brief pause)", speaker="persona"),
            FakeTranscriptSegment(text="I just wanted to check in about senior placement.", speaker="persona"),
        ]
    )
    output, _ = await run_runtime(provider, make_session_context(tmp_path))
    assert output.disclosure_completed is True
    assert output.human_review_reason is None, (
        "absence of explicit acknowledgment must not escalate needs_human_review (Round 1 Q1)"
    )
