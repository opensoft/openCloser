"""Test fakes for the Pipecat runtime surface (T014 contract test fixtures).

``FakeRealtimeAIProvider`` implements the ``RealtimeAIProvider`` Protocol
from ``opencloser.runtime.base`` so contract tests can exercise
``PipecatRuntime.run(...)`` without burning real provider credentials.

The fake supports several scripted modes — each test case configures the
behavior it wants, then asserts the orchestrator's persona output.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from opencloser.persona.base import SessionContext


@dataclass(frozen=True)
class FakeSessionHandle:
    """Implements the ``SessionHandle`` Protocol structurally."""

    session_id: str


# Frame types the fake emits — kept duck-typed so the runtime adapter can
# define the real frame types in ``runtime/pipecat/pipeline.py`` (T029).
@dataclass(frozen=True)
class FakeTranscriptSegment:
    text: str
    speaker: str = "caller"  # "caller" | "persona"


@dataclass(frozen=True)
class FakeExtractionEvent:
    field: str
    value: Any
    confidence: float = 1.0


@dataclass
class FakeRealtimeAIProvider:
    """Scriptable in-memory fake of the deployment-configured real-time AI
    provider.

    Modes:

    - ``scripted_extractions`` — replay a queue of transcript/extraction
      frames on each ``stream_audio`` call.
    - ``raise_on_start`` — raise the named exception in ``start_session``.
    - ``raise_during_stream`` — raise the named exception after the Nth
      ``stream_audio`` chunk.
    - ``silent_after_connection`` — yield 0 transcript/extraction frames
      until the silence timeout fires.
    """

    provider_name: str = "fake-realtime"
    model_name: str = "fake-realtime-1"
    model_version: str = "test-0.1"
    scripted_frames: list[FakeTranscriptSegment | FakeExtractionEvent] = field(default_factory=list)
    raise_on_start: type[Exception] | None = None
    raise_during_stream: type[Exception] | None = None
    raise_after_chunks: int = 0
    silent_after_connection: bool = False
    chunks_streamed: int = 0
    started: bool = False
    ended: bool = False

    @property
    def identity(self) -> dict[str, str]:
        # MUST NOT include credentials per FR-035.
        return {
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "model_version": self.model_version,
        }

    async def start_session(self, session_context: SessionContext) -> FakeSessionHandle:
        if self.raise_on_start is not None:
            raise self.raise_on_start(f"fake-provider start failure for session={session_context.session_id}")
        self.started = True
        return FakeSessionHandle(session_id=session_context.session_id)

    async def stream_audio(
        self,
        handle: FakeSessionHandle,
        audio_chunk: bytes,
    ) -> AsyncIterator[FakeTranscriptSegment | FakeExtractionEvent]:
        self.chunks_streamed += 1
        if self.raise_during_stream is not None and self.chunks_streamed >= self.raise_after_chunks:
            raise self.raise_during_stream(f"fake-provider stream failure on chunk {self.chunks_streamed}")
        if self.silent_after_connection:
            return _empty_stream()
        return _replay(self.scripted_frames)

    async def end_session(self, handle: FakeSessionHandle) -> None:
        self.ended = True


async def _empty_stream() -> AsyncIterator[Any]:
    if False:
        yield  # pragma: no cover


async def _replay(frames: list[Any]) -> AsyncIterator[Any]:
    for frame in frames:
        yield frame


@dataclass
class FakeLiveConversationInput:
    """Implements ``LiveConversationInput`` Protocol structurally. Replays a
    fixed list of inbound audio chunks (each a ``bytes`` blob)."""

    session_id_value: str = "fake-session"
    audio_chunks: list[bytes] = field(default_factory=lambda: [b"\x00" * 160])

    @property
    def session_id(self) -> str:
        return self.session_id_value

    @property
    def audio_in(self) -> AsyncIterator[bytes]:
        return self._audio_iter()

    async def _audio_iter(self) -> AsyncIterator[bytes]:
        for chunk in self.audio_chunks:
            yield chunk
