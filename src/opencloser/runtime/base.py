"""Slice 3 — `PersonaRuntime` conceptual contract (FR-013, FR-014, FR-016).

This module defines the *Protocol* the orchestrator depends on. The concrete
Pipecat + real-time-AI-provider implementation lands in ``runtime/pipecat/``
(US1 + US5). The Slice 1 ``Persona.run(session_context, conversation) →
PersonaOutput`` signature is preserved verbatim per FR-018 — Slice 3 just
swaps the input ``conversation`` from a scripted ``ConversationFixture`` to a
live media stream driven by the Pipecat pipeline.

See ``specs/003-real-call-real-crm/contracts/pipecat-runtime.md`` for the full
contract, including required behaviors and the contract-test enumeration.

What MUST NOT leak past this boundary (per Constitution Principle III):

- Pipecat-specific ``FrameProcessor`` / ``Pipeline`` / ``Transport`` types
- The real-time AI provider's streaming protocol details
- Audio codec / sample-rate / VAD configuration
- Credentials
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

# Reuse the Slice 1 types verbatim per FR-018 (no module-boundary widening).
from opencloser.persona.base import PersonaOutput, SessionContext


class LiveConversationInput(Protocol):
    """The live-conversation input the Pipecat runtime consumes.

    Distinct from the Slice 1 ``ConversationFixture`` (scripted) — Slice 3's
    runtime gets a live audio stream + extraction events flowing from
    SignalWire through Pipecat to the configured real-time AI provider. Kept
    as a structural Protocol so the runtime adapter can accept any object that
    exposes the audio stream + the mounting points the persona module needs.

    Concrete shape lands in ``runtime/pipecat/pipeline.py`` (US1 T029).
    """

    @property
    def audio_in(self) -> AsyncIterator[bytes]:
        """Inbound caller audio frames (μ-law 8 kHz per research.md §5)."""
        ...

    @property
    def session_id(self) -> str:
        """The owning session — used by the runtime to record identity per FR-016."""
        ...


class PersonaRuntime(Protocol):
    """The Slice 3 persona-runtime contract.

    Concrete implementation: ``opencloser.runtime.pipecat.runtime.PipecatRuntime``
    (lands in US1 + US5). The orchestrator depends only on this Protocol, never
    on the concrete class — preserving the Slice 1 boundary per FR-018.
    """

    async def run(
        self,
        session_context: SessionContext,
        conversation: LiveConversationInput,
    ) -> PersonaOutput:
        """Drive the connected-call conversation and return the persona's output.

        Required behaviors (see ``contracts/pipecat-runtime.md`` for full
        normative wording):

        1. The first connected-call utterance MUST include the canonical
           AI-on-behalf-of-Medx disclosure (FR-015). No explicit verbal
           acknowledgment from the caller is required (Round 1 Q1).
        2. The runtime MAY produce conversation turns and extraction events,
           but MUST NOT set the final disposition — the persona module's
           deterministic Slice 1 disposition precedence (FR-014) owns that.
        3. The runtime MUST NOT expand or replace the ``HumanReviewReason``
           enumeration; only the additive ``shadow_stt_discrepancy`` entry is
           sanctioned, and it is emitted by the shadow STT lane (not here).
        4. On caller-volunteered PHI (per Round 2 Q11), the runtime MUST
           escalate ``needs_human_review`` with reason ``phi_collection_risk``
           AND invoke the redaction layer's PHI tag-and-redact pass on the
           in-flight transcript / summary / shadow transcript / shadow
           discrepancy buffer before any artifact write.

        Raises:
            RealtimeProviderError: provider-side failure (FR-013 Round 1 Q4 (a)).
            PipecatRuntimeError: runtime crash / unrecoverable adapter failure
                (FR-013 Round 1 Q4 (b)).
            SilenceAfterConnectionTimeout: deployment-configurable silence /
                no-extraction-event timeout elapsed (FR-013 Round 1 Q4 (c)).
        """
        ...


class RealtimeAIProvider(Protocol):
    """The deployment-configured real-time AI model provider surface (research.md §3).

    Consumed by ``runtime/pipecat/runtime.py`` (US1). Concrete implementations
    land in ``runtime/pipecat/provider.py`` per the first supported provider;
    a fake for CI lands in ``runtime/pipecat/provider_fake.py``.

    The runtime adapter MUST NOT leak this provider's SDK return types or
    streaming-protocol details past the Pipecat module boundary.
    """

    async def start_session(self, session_context: SessionContext) -> "SessionHandle":
        """Open a streaming session with the provider."""
        ...

    async def stream_audio(self, handle: "SessionHandle", audio_chunk: bytes) -> object:
        """Stream one audio chunk; yield audio / transcript / extraction frames.

        The concrete return type is an async iterator of frame variants whose
        public surface is defined in ``runtime/pipecat/pipeline.py``. Kept as
        ``object`` here so the boundary stays vendor-agnostic.
        """
        ...

    async def end_session(self, handle: "SessionHandle") -> None:
        """Close the streaming session and release provider-side resources."""
        ...

    @property
    def identity(self) -> dict[str, str]:
        """Return ``{provider_name, model_name, model_version}`` for audit (FR-016).

        MUST NOT include credentials (FR-035). Recorded on every session and
        surfaced in the run report.
        """
        ...


class SessionHandle(Protocol):
    """Opaque per-session handle returned by ``RealtimeAIProvider.start_session``.

    The runtime adapter never inspects this; it is passed back to ``stream_audio``
    and ``end_session`` so the provider can correlate frames with the session.
    """

    @property
    def session_id(self) -> str:
        """Session identifier for the provider-side correlation."""
        ...
