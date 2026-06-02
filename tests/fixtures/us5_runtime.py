"""Shared US5 live-conversation runtime driver (T058-T063).

The US5 persona-safety integration tests exercise the live ``PipecatRuntime``
path against the ``FakeRealtimeAIProvider`` fixtures (the same fakes the T014
contract test injects), so they verify the connected-call safety behaviors
end-to-end without burning provider credentials or placing a real call.

This module centralizes the ``SessionContext`` + runtime wiring every US5 [P]
test shares (one helper, not five copies — same duplication rationale as
``slice3_configs.py``).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from opencloser.core.clock import FrozenClock
from opencloser.models import (
    ArtifactsConfig,
    CallableStatus,
    CallWindowConfig,
    EligibilityConfig,
    PersonaConfig,
    QueueItem,
    SliceConfig,
    StateConfig,
)
from opencloser.persona.base import SessionContext
from opencloser.runtime.pipecat.runtime import PipecatRuntime
from tests.fixtures.pipecat import FakeLiveConversationInput, FakeRealtimeAIProvider

_SESSION_ID = "sess-us5-001"


def make_session_context(tmp_path: Path) -> SessionContext:
    config = SliceConfig(
        call_window=CallWindowConfig(start="09:00", end="20:00"),
        eligibility=EligibilityConfig(max_attempts=5, default_timezone="America/Los_Angeles"),
        artifacts=ArtifactsConfig(dir=str(tmp_path / "artifacts")),
        persona=PersonaConfig(version="alf-appointment-setter@0.1.0"),
        state=StateConfig(db=str(tmp_path / "state.db")),
    )
    queue_item = QueueItem(
        queue_item_id="alf-prospect-us5",
        facility_name="Sunset Ridge ALF",
        phone_number="+15555550100",
        timezone="America/Los_Angeles",
        attempt_count=0,
        callable_status=CallableStatus.READY,
    )
    return SessionContext(
        session_id=_SESSION_ID,
        queue_item=queue_item,
        mock_provider_call_id="CA-US5-FAKE",
        started_at="2026-05-25T14:00:00.000Z",
        config=config,
        clock=FrozenClock(datetime(2026, 5, 25, 14, 0, 0, tzinfo=UTC)),
    )


def conversation_input() -> FakeLiveConversationInput:
    return FakeLiveConversationInput(session_id_value=_SESSION_ID)


async def run_runtime(
    provider: FakeRealtimeAIProvider,
    session_context: SessionContext,
    *,
    silence_after_connection_timeout_sec: int = 30,
    shadow_stt_enabled: bool = True,
):
    """Drive ``PipecatRuntime.run`` against the supplied fake provider.

    Returns ``(output, runtime)`` so callers can assert both the persona output
    and the runtime's surfaced ``degradation_reason`` / ``phi_volunteered``.
    """
    runtime = PipecatRuntime(
        provider=provider,
        silence_after_connection_timeout_sec=silence_after_connection_timeout_sec,
        shadow_stt_enabled=shadow_stt_enabled,
    )
    output = await runtime.run(session_context, conversation_input())
    return output, runtime
