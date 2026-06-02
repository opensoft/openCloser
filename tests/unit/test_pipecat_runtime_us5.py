"""Unit tests for the US5 runtime edge paths (transient connect retry + safe end)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from opencloser.core.clock import FrozenClock
from opencloser.models import (
    ArtifactsConfig,
    CallableStatus,
    CallWindowConfig,
    Disposition,
    EligibilityConfig,
    PersonaConfig,
    QueueItem,
    SliceConfig,
    StateConfig,
)
from opencloser.persona.alf_appointment_setter import CANONICAL_DISCLOSURE
from opencloser.persona.base import SessionContext
from opencloser.runtime.pipecat.errors import RealtimeProviderError
from opencloser.runtime.pipecat.runtime import PipecatRuntime
from tests.fixtures.pipecat import (
    FakeLiveConversationInput,
    FakeSessionHandle,
    FakeTranscriptSegment,
)


def _ctx(tmp_path: Path) -> SessionContext:
    config = SliceConfig(
        call_window=CallWindowConfig(start="09:00", end="20:00"),
        eligibility=EligibilityConfig(max_attempts=5, default_timezone="America/Los_Angeles"),
        artifacts=ArtifactsConfig(dir=str(tmp_path / "artifacts")),
        persona=PersonaConfig(version="alf-appointment-setter@0.1.0"),
        state=StateConfig(db=str(tmp_path / "state.db")),
    )
    return SessionContext(
        session_id="sess-unit",
        queue_item=QueueItem(
            queue_item_id="q1",
            facility_name="F",
            phone_number="+15555550100",
            timezone="America/Los_Angeles",
            attempt_count=0,
            callable_status=CallableStatus.READY,
        ),
        mock_provider_call_id="CA-UNIT",
        started_at="2026-05-25T14:00:00.000Z",
        config=config,
        clock=FrozenClock(datetime(2026, 5, 25, 14, 0, 0, tzinfo=UTC)),
    )


class _TransientThenOkProvider:
    """Raises a TRANSIENT RealtimeProviderError on the first N start attempts,
    then connects normally (R4-Q5: retried within the connect budget)."""

    provider_name = "fake"
    model_name = "fake-1"
    model_version = "0.1"

    def __init__(self, fail_times: int) -> None:
        self._fail_times = fail_times
        self.starts = 0
        self.ended = False

    @property
    def identity(self) -> dict[str, str]:
        return {
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "model_version": self.model_version,
        }

    async def start_session(self, session_context: SessionContext) -> FakeSessionHandle:
        self.starts += 1
        if self.starts <= self._fail_times:
            raise RealtimeProviderError("transient", transient=True)
        return FakeSessionHandle(session_id=session_context.session_id)

    async def stream_audio(self, handle, audio_chunk) -> AsyncIterator:
        async def _gen():
            yield FakeTranscriptSegment(text=CANONICAL_DISCLOSURE, speaker="persona")
            yield FakeTranscriptSegment(text="Sure.", speaker="caller")

        return _gen()

    async def end_session(self, handle) -> None:
        self.ended = True


class _EndFailsProvider(_TransientThenOkProvider):
    """Connects fine but raises on end_session — the runtime must not let the
    end_session failure mask the conversation outcome."""

    async def end_session(self, handle) -> None:
        raise RealtimeProviderError("end failure")


@pytest.mark.asyncio
async def test_transient_connect_error_is_retried(tmp_path: Path) -> None:
    provider = _TransientThenOkProvider(fail_times=2)
    runtime = PipecatRuntime(provider=provider)
    output = await runtime.run(_ctx(tmp_path), FakeLiveConversationInput(session_id_value="sess-unit"))
    assert provider.starts == 3  # 2 transient failures + 1 success within the budget
    assert runtime.degradation_reason is None
    assert output.disclosure_completed is True


@pytest.mark.asyncio
async def test_transient_connect_budget_exhausted_yields_failed(tmp_path: Path) -> None:
    provider = _TransientThenOkProvider(fail_times=99)  # always transient-fails
    runtime = PipecatRuntime(provider=provider)
    output = await runtime.run(_ctx(tmp_path), FakeLiveConversationInput(session_id_value="sess-unit"))
    assert output.final_disposition is Disposition.FAILED
    assert runtime.degradation_reason == "provider_error"


@pytest.mark.asyncio
async def test_end_session_failure_does_not_mask_outcome(tmp_path: Path) -> None:
    provider = _EndFailsProvider(fail_times=0)
    runtime = PipecatRuntime(provider=provider)
    output = await runtime.run(_ctx(tmp_path), FakeLiveConversationInput(session_id_value="sess-unit"))
    assert output.disclosure_completed is True
    assert runtime.degradation_reason is None
