"""In-tree development / CI fake real-time AI provider (research.md §3).

``FakeRealtimeAIProvider`` implements the
:class:`~opencloser.runtime.base.RealtimeAIProvider` Protocol so the Pipecat
pipeline (T029) and runtime (T030) can be exercised in CI / rehearsal without
burning real-provider tokens. It replays a scripted list of vendor-neutral
frames (:class:`TranscriptSegment` / :class:`ExtractionEvent` from
``provider.py``) on each ``stream_audio`` call.

This is the *source-tree* fake the runtime selects via
:func:`provider.select_realtime_provider`. The richer error-injection fake used
by the T014 contract test lives separately in ``tests/fixtures/pipecat/``.

The identity (``provider_name`` / ``model_name`` / ``model_version``) carries no
credentials per FR-035.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from opencloser.persona.base import SessionContext
from opencloser.runtime.pipecat.provider import (
    ExtractionEvent,
    ProviderSessionHandle,
    TranscriptSegment,
)

_Frame = TranscriptSegment | ExtractionEvent


@dataclass
class FakeRealtimeAIProvider:
    """Scriptable in-process fake of the deployment-configured provider."""

    provider_name: str = "fake-realtime"
    model_name: str = "fake-realtime-1"
    model_version: str = "dev-0.1"
    scripted_frames: list[_Frame] = field(default_factory=list)
    started: bool = False
    ended: bool = False

    @property
    def identity(self) -> dict[str, str]:
        # MUST NOT include credentials (FR-035).
        return {
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "model_version": self.model_version,
        }

    async def start_session(self, session_context: SessionContext) -> ProviderSessionHandle:
        self.started = True
        return ProviderSessionHandle(session_id=session_context.session_id)

    async def stream_audio(
        self,
        handle: ProviderSessionHandle,
        audio_chunk: bytes,
    ) -> AsyncIterator[_Frame]:
        """Replay the scripted frames once per call. Returns an async iterator."""
        return _replay(self.scripted_frames)

    async def end_session(self, handle: ProviderSessionHandle) -> None:
        self.ended = True


async def _replay(frames: list[_Frame]) -> AsyncIterator[_Frame]:
    for frame in frames:
        yield frame
