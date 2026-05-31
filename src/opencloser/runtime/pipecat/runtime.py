"""Slice 3 Pipecat runtime — the concrete ``PersonaRuntime`` implementation.

Stub module — bodies land in T030 (real impl) + T064/T065 (degradation
triggers) + T066/T067 (PHI escalation wiring). Per T013 Q5 the contract
test (T014) imports ``PipecatRuntime`` and constructs it; each method body
raises ``NotImplementedError`` so the 11 contract assertions fail at
assertion time with a clear "expected X, got NotImplementedError" message.

This module MUST NOT leak Pipecat-specific ``FrameProcessor`` / ``Pipeline``
/ ``Transport`` types, audio codec / sample-rate / VAD configuration, or
the real-time AI provider's streaming protocol details past its public
surface (Constitution Principle III; FR-013; SC-015).
"""

from __future__ import annotations

from opencloser.persona.base import PersonaOutput, SessionContext
from opencloser.runtime.base import LiveConversationInput, RealtimeAIProvider


class PipecatRuntime:
    """The ``PersonaRuntime`` Protocol's Slice 3 concrete implementation.

    ``RealtimeAIProvider`` is constructor-injected so contract tests can
    pass a ``FakeRealtimeAIProvider`` (see
    ``tests/fixtures/pipecat/__init__.py``) without burning real
    provider credentials.
    """

    def __init__(
        self,
        *,
        provider: RealtimeAIProvider,
        silence_after_connection_timeout_sec: int = 30,
    ) -> None:
        self._provider = provider
        self._silence_timeout_sec = silence_after_connection_timeout_sec

    async def run(
        self,
        session_context: SessionContext,
        conversation: LiveConversationInput,
    ) -> PersonaOutput:
        """Drive the connected-call conversation and return the persona's output.

        See ``contracts/pipecat-runtime.md`` Required Behaviors #1-#6 for the
        normative wording. Stub raises ``NotImplementedError``; real impl lands
        in T030 (pipeline wiring) + T064/T065 (degradation triggers) + T066/T067
        (PHI escalation + redaction).
        """

        raise NotImplementedError("T030 / T064 / T065 — PipecatRuntime.run not yet implemented")  # pragma: no cover
