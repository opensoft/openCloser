"""Slice 3 Pipecat runtime — the concrete ``PersonaRuntime`` implementation (T030).

``PipecatRuntime.run`` drives one connected-call conversation:

1. Open a provider session (``RealtimeAIProvider.start_session``).
2. Stream the caller audio (from the ``LiveConversationInput``) through the
   provider, collecting the transcript frames it yields.
3. Record the runtime/model identity (FR-016, via ``identity.py`` T027).
4. Hand the transcript to the persona module, whose **deterministic Slice 1
   disposition precedence** selects the final disposition (FR-014). A live-model
   ``ExtractionEvent`` is never allowed to set the disposition — extraction
   frames are dropped here; only transcript turns reach the persona.

This module MUST NOT leak Pipecat ``FrameProcessor`` / ``Pipeline`` / ``Transport``
types, audio codec / sample-rate / VAD configuration, or the provider's
streaming-protocol details past its public surface (Constitution Principle III;
SC-015) — it imports none of them.

**Deferred to US5**: the three runtime-degradation triggers (pre-/post-connected
provider failure, silence-after-connection timeout) land in ``degradation.py``
+ this module's wiring (T064/T065); caller-volunteered-PHI escalation +
tag-and-redact lands in the persona extraction hook (T066/T067). Until then the
degradation / PHI contract-test assertions (T014 #5-#9) stay red.
"""

from __future__ import annotations

from opencloser.persona.alf_appointment_setter import ALFAppointmentSetterPersona
from opencloser.persona.base import (
    ConversationFixture,
    ConversationTurn,
    Persona,
    PersonaOutput,
    SessionContext,
)
from opencloser.runtime.base import LiveConversationInput, RealtimeAIProvider
from opencloser.runtime.pipecat.identity import build_runtime_identity


class PipecatRuntime:
    """The ``PersonaRuntime`` Protocol's Slice 3 concrete implementation.

    ``RealtimeAIProvider`` is constructor-injected so contract tests can pass a
    ``FakeRealtimeAIProvider`` without burning real provider credentials. The
    persona defaults to the ALF appointment-setter (the only Slice 1/2/3 persona);
    an explicit ``persona`` may be injected for testing.
    """

    def __init__(
        self,
        *,
        provider: RealtimeAIProvider,
        silence_after_connection_timeout_sec: int = 30,
        persona: Persona | None = None,
    ) -> None:
        self._provider = provider
        self._silence_timeout_sec = silence_after_connection_timeout_sec
        self._persona = persona or ALFAppointmentSetterPersona()

    async def run(
        self,
        session_context: SessionContext,
        conversation: LiveConversationInput,
    ) -> PersonaOutput:
        """Drive the connected-call conversation and return the persona's output.

        See ``contracts/pipecat-runtime.md`` Required Behaviors #1-#4. Degradation
        (#5) and PHI escalation (Round 2 Q11) are wired in US5 (T064-T067).
        """
        handle = await self._provider.start_session(session_context)
        turns: list[ConversationTurn] = []
        try:
            async for audio_chunk in conversation.audio_in:
                frames = await self._provider.stream_audio(handle, audio_chunk)
                async for frame in frames:
                    turn = _frame_to_turn(frame)
                    if turn is not None:
                        turns.append(turn)
        finally:
            await self._provider.end_session(handle)

        # Record runtime/model identity for audit (FR-016); credentials excluded
        # (FR-035). Held for the run report (T033) to surface.
        self._runtime_identity = build_runtime_identity(self._provider)

        # The persona module owns the deterministic disposition precedence
        # (FR-014). Live-model extraction frames never reach it.
        fixture = ConversationFixture(
            fixture_id=session_context.session_id,
            expected_disposition="",  # tests-only field; the persona ignores it
            queue_item_ref=session_context.queue_item.queue_item_id,
            turns=turns,
            expected_extraction={},
        )
        return self._persona.run(session_context, fixture)


def _frame_to_turn(frame: object) -> ConversationTurn | None:
    """Map a provider transcript frame to a conversation turn.

    Duck-typed so both the in-tree ``provider.py`` frames and the contract-test
    fakes work. Non-transcript frames (extraction / audio) return ``None`` — an
    ``ExtractionEvent`` MUST NOT influence the disposition (FR-014), so it never
    becomes a turn.
    """
    text = getattr(frame, "text", None)
    speaker = getattr(frame, "speaker", None)
    if text is None or speaker is None:
        return None
    role = "persona" if speaker == "persona" else "contact"
    return ConversationTurn(role=role, text=text)
