"""T062 — US5 integration: runtime degradation triggers (FR-013 Round 1 Q4).

The three live-runtime degradation triggers and their disposition mapping
(contract Required-Behavior #5):

- pre-connected (a) ``RealtimeProviderError`` / (b) ``PipecatRuntimeError`` on
  start → ``failed`` with the runtime-failure reason; no false connected-call
  activity.
- post-connected (any of (a) / (b) / (c) silence-after-connection timeout) →
  ``needs_human_review`` / ``script_truncated``.

Each trigger also maps to a DISTINCT run-report reason code (R4-Q13):
``provider_error`` / ``runtime_crash`` / ``silence_timeout``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from opencloser.models import Disposition, HumanReviewReason
from opencloser.persona.alf_appointment_setter import CANONICAL_DISCLOSURE
from opencloser.runtime.pipecat.errors import (
    PipecatRuntimeError,
    RealtimeProviderError,
)
from tests.fixtures.pipecat import FakeRealtimeAIProvider, FakeTranscriptSegment
from tests.fixtures.us5_runtime import make_session_context, run_runtime

pytestmark = pytest.mark.integration


# ----- pre-connected -------------------------------------------------------


@pytest.mark.asyncio
async def test_provider_error_pre_connected_yields_failed(tmp_path: Path) -> None:
    provider = FakeRealtimeAIProvider(raise_on_start=RealtimeProviderError)
    output, runtime = await run_runtime(provider, make_session_context(tmp_path))
    assert output.final_disposition is Disposition.FAILED
    assert output.human_review_reason is None
    assert runtime.degradation_reason == "provider_error"


@pytest.mark.asyncio
async def test_runtime_crash_pre_connected_yields_failed(tmp_path: Path) -> None:
    provider = FakeRealtimeAIProvider(raise_on_start=PipecatRuntimeError)
    output, runtime = await run_runtime(provider, make_session_context(tmp_path))
    assert output.final_disposition is Disposition.FAILED
    assert output.human_review_reason is None
    assert runtime.degradation_reason == "runtime_crash"


# ----- post-connected ------------------------------------------------------


@pytest.mark.asyncio
async def test_provider_error_post_connected_yields_review(tmp_path: Path) -> None:
    provider = FakeRealtimeAIProvider(
        scripted_frames=[FakeTranscriptSegment(text=CANONICAL_DISCLOSURE, speaker="persona")],
        raise_during_stream=RealtimeProviderError,
        raise_after_chunks=1,
    )
    output, runtime = await run_runtime(provider, make_session_context(tmp_path))
    assert output.final_disposition is Disposition.NEEDS_HUMAN_REVIEW
    assert output.human_review_reason is HumanReviewReason.SCRIPT_TRUNCATED
    assert runtime.degradation_reason == "provider_error"


@pytest.mark.asyncio
async def test_runtime_crash_post_connected_yields_review(tmp_path: Path) -> None:
    provider = FakeRealtimeAIProvider(
        scripted_frames=[FakeTranscriptSegment(text=CANONICAL_DISCLOSURE, speaker="persona")],
        raise_during_stream=PipecatRuntimeError,
        raise_after_chunks=1,
    )
    output, runtime = await run_runtime(provider, make_session_context(tmp_path))
    assert output.final_disposition is Disposition.NEEDS_HUMAN_REVIEW
    assert output.human_review_reason is HumanReviewReason.SCRIPT_TRUNCATED
    assert runtime.degradation_reason == "runtime_crash"


@pytest.mark.asyncio
async def test_silence_after_connection_timeout_yields_review(tmp_path: Path) -> None:
    provider = FakeRealtimeAIProvider(
        scripted_frames=[FakeTranscriptSegment(text=CANONICAL_DISCLOSURE, speaker="persona")],
        silent_after_connection=True,
    )
    output, runtime = await run_runtime(
        provider, make_session_context(tmp_path), silence_after_connection_timeout_sec=1
    )
    assert output.final_disposition is Disposition.NEEDS_HUMAN_REVIEW
    assert output.human_review_reason is HumanReviewReason.SCRIPT_TRUNCATED
    assert runtime.degradation_reason == "silence_timeout"


def test_three_triggers_map_to_distinct_reason_codes() -> None:
    """R4-Q13: the three triggers map to three DISTINCT run-report reason codes."""
    from opencloser.runtime.pipecat.degradation import DegradationReason

    codes = {
        DegradationReason.PROVIDER_ERROR.value,
        DegradationReason.RUNTIME_CRASH.value,
        DegradationReason.SILENCE_TIMEOUT.value,
    }
    assert codes == {"provider_error", "runtime_crash", "silence_timeout"}
