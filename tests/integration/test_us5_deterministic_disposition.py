"""T061 — US5 integration: deterministic disposition precedence (FR-014, SC-014).

The live model may emit an ``ExtractionEvent`` (and conversation turns), but the
deterministic Slice 1 disposition rules — applied to the EXTRACTED state — own
the final disposition. A live-model ``ExtractionEvent.disposition`` injection
MUST be ignored; the disposition equals the deterministic-rule output for the
actual extracted state, not the live-model-chosen value.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from opencloser.models import Disposition
from opencloser.persona.alf_appointment_setter import CANONICAL_DISCLOSURE
from tests.fixtures.pipecat import (
    FakeExtractionEvent,
    FakeRealtimeAIProvider,
    FakeTranscriptSegment,
)
from tests.fixtures.us5_runtime import make_session_context, run_runtime

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_live_model_disposition_injection_ignored_opt_out_wins(tmp_path: Path) -> None:
    """The live model injects ``disposition=interested_callback_requested`` while
    the caller clearly opts out. The deterministic rule maps the opt-out to
    ``do_not_call`` and the injection is ignored."""
    provider = FakeRealtimeAIProvider(
        scripted_frames=[
            FakeTranscriptSegment(text=CANONICAL_DISCLOSURE, speaker="persona"),
            FakeExtractionEvent(
                field="disposition", value="interested_callback_requested", confidence=0.99
            ),
            FakeTranscriptSegment(text="Please don't call me again.", speaker="caller"),
        ]
    )
    output, _ = await run_runtime(provider, make_session_context(tmp_path))
    assert output.final_disposition is Disposition.DO_NOT_CALL, (
        "deterministic opt-out rule wins; live-model disposition injection is ignored"
    )


@pytest.mark.asyncio
async def test_live_model_disposition_injection_ignored_callback_wins(tmp_path: Path) -> None:
    """A different extracted state (a genuine callback request) deterministically
    maps to ``interested_callback_requested`` regardless of a conflicting
    live-model injection."""
    provider = FakeRealtimeAIProvider(
        scripted_frames=[
            FakeTranscriptSegment(text=CANONICAL_DISCLOSURE, speaker="persona"),
            FakeExtractionEvent(field="disposition", value="do_not_call", confidence=0.99),
            FakeTranscriptSegment(
                text=(
                    "I'm the administrator here and I'm interested — please call me "
                    "back on Thursday at 2 PM."
                ),
                speaker="caller",
            ),
        ]
    )
    output, _ = await run_runtime(provider, make_session_context(tmp_path))
    assert output.final_disposition is Disposition.INTERESTED_CALLBACK_REQUESTED, (
        "deterministic callback rule wins; live-model disposition injection is ignored"
    )
