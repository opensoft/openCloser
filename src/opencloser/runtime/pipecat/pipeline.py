"""Slice 3 Pipecat pipeline topology (research.md §5).

A single linear Pipecat ``FrameProcessor`` chain with three stages:

1. :class:`SignalWireMediaInput` — adapts SignalWire media bytes to Pipecat
   ``InputAudioRawFrame`` (μ-law 8 kHz, matching SignalWire's default codec).
2. :class:`RealtimeAIProviderBridge` — delegates audio frames to the configured
   :class:`~opencloser.runtime.base.RealtimeAIProvider` (T028) and emits
   vendor-neutral persona frames (transcript + extraction).
3. :class:`PersonaSink` — collects the persona frames so the runtime (T030) can
   hand them to the persona module, where the deterministic Slice 1 disposition
   precedence selects the final disposition (FR-014 — the live model never sets
   it).

Turn-taking is VAD-driven via the provider's built-in turn-taking with an
800 ms silence-after-speech fallback (:data:`PipelineConfig.vad_silence_ms`).

This module is the *production* media-transport wiring. The contract test
(T014) drives the runtime (T030) with in-memory fakes rather than a live Pipecat
pipeline, so — like ``runtime.py`` — this module's ``FrameProcessor.process_frame``
integration (which requires Pipecat's live pipeline setup) is exercised by
integration/manual runs, not unit tests; the pure translation helpers and
assembly are unit-tested in ``tests/unit/test_pipecat_pipeline.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pipecat.frames.frames import Frame, InputAudioRawFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from opencloser.runtime.pipecat.provider import (
    ExtractionEvent,
    ProviderSessionHandle,
    TranscriptSegment,
)

if TYPE_CHECKING:
    from opencloser.runtime.base import RealtimeAIProvider

# Audio codec + turn-taking (research.md §5). μ-law 8 kHz matches SignalWire's
# default voice codec; 800 ms is the silence-after-speech turn-taking fallback.
AUDIO_ENCODING = "mulaw"
SAMPLE_RATE_HZ = 8000
NUM_CHANNELS = 1
VAD_SILENCE_MS = 800


@dataclass(frozen=True)
class PipelineConfig:
    """Audio + turn-taking configuration for the Slice 3 pipeline (research.md §5)."""

    audio_encoding: str = AUDIO_ENCODING
    sample_rate_hz: int = SAMPLE_RATE_HZ
    num_channels: int = NUM_CHANNELS
    vad_silence_ms: int = VAD_SILENCE_MS


@dataclass
class PersonaTranscriptFrame(Frame):
    """Pipecat frame carrying a vendor-neutral :class:`TranscriptSegment` downstream."""

    segment: TranscriptSegment | None = None


@dataclass
class PersonaExtractionFrame(Frame):
    """Pipecat frame carrying a vendor-neutral :class:`ExtractionEvent` downstream."""

    event: ExtractionEvent | None = None


def media_bytes_to_audio_frame(chunk: bytes, config: PipelineConfig) -> InputAudioRawFrame:
    """Wrap one inbound SignalWire media chunk as a Pipecat audio frame."""
    return InputAudioRawFrame(
        audio=chunk,
        sample_rate=config.sample_rate_hz,
        num_channels=config.num_channels,
    )


def provider_frame_to_persona_frame(
    frame: object,
) -> PersonaTranscriptFrame | PersonaExtractionFrame | None:
    """Translate a provider output frame into a downstream persona frame.

    Unknown frame types (e.g. provider audio frames) return ``None`` and are
    absorbed — only persona-relevant transcript/extraction data flows to the sink.
    """
    if isinstance(frame, TranscriptSegment):
        return PersonaTranscriptFrame(segment=frame)
    if isinstance(frame, ExtractionEvent):
        return PersonaExtractionFrame(event=frame)
    return None


class SignalWireMediaInput(FrameProcessor):
    """Stage 1 — adapt SignalWire media bytes to Pipecat audio frames."""

    def __init__(self, *, config: PipelineConfig) -> None:
        super().__init__()
        self._config = config

    async def push_media(self, chunk: bytes) -> None:
        """Push one inbound media chunk downstream as a Pipecat audio frame."""
        await self.push_frame(
            media_bytes_to_audio_frame(chunk, self._config),
            FrameDirection.DOWNSTREAM,
        )


class RealtimeAIProviderBridge(FrameProcessor):
    """Stage 2 — delegate audio frames to the provider; emit persona frames."""

    def __init__(self, *, provider: RealtimeAIProvider, handle: ProviderSessionHandle) -> None:
        super().__init__()
        self._provider = provider
        self._handle = handle

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, InputAudioRawFrame):
            async for provider_frame in await self._provider.stream_audio(self._handle, frame.audio):
                persona_frame = provider_frame_to_persona_frame(provider_frame)
                if persona_frame is not None:
                    await self.push_frame(persona_frame, FrameDirection.DOWNSTREAM)
        else:
            await self.push_frame(frame, direction)


class PersonaSink(FrameProcessor):
    """Stage 3 — collect persona transcript + extraction frames for the runtime."""

    def __init__(self) -> None:
        super().__init__()
        self.collected: list[TranscriptSegment | ExtractionEvent] = []

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, PersonaTranscriptFrame) and frame.segment is not None:
            self.collected.append(frame.segment)
        elif isinstance(frame, PersonaExtractionFrame) and frame.event is not None:
            self.collected.append(frame.event)
        await self.push_frame(frame, direction)


@dataclass
class BuiltPipeline:
    """The assembled pipeline plus its stages (the runtime reads ``sink.collected``)."""

    pipeline: Pipeline
    media_input: SignalWireMediaInput
    bridge: RealtimeAIProviderBridge
    sink: PersonaSink


def build_pipeline(
    *,
    provider: RealtimeAIProvider,
    handle: ProviderSessionHandle,
    config: PipelineConfig | None = None,
) -> BuiltPipeline:
    """Assemble the three-stage Slice 3 Pipecat pipeline (research.md §5)."""
    cfg = config or PipelineConfig()
    media_input = SignalWireMediaInput(config=cfg)
    bridge = RealtimeAIProviderBridge(provider=provider, handle=handle)
    sink = PersonaSink()
    pipeline = Pipeline([media_input, bridge, sink])
    return BuiltPipeline(pipeline=pipeline, media_input=media_input, bridge=bridge, sink=sink)
