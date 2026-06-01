"""T029 — unit tests for the Pipecat pipeline topology (pipeline.py) per research.md §5.

Covers the pure, unit-testable surface: the audio/turn-taking config, the
media-bytes → audio-frame and provider-frame → persona-frame translation
helpers, and the three-stage assembly. The live ``FrameProcessor.process_frame``
delivery path requires Pipecat's pipeline runtime and is exercised by
integration/manual runs (pipeline.py is coverage-omitted for that reason).
"""

from __future__ import annotations

from pipecat.frames.frames import InputAudioRawFrame
from pipecat.pipeline.pipeline import Pipeline

from opencloser.runtime.pipecat.pipeline import (
    AUDIO_ENCODING,
    SAMPLE_RATE_HZ,
    VAD_SILENCE_MS,
    PersonaExtractionFrame,
    PersonaSink,
    PersonaTranscriptFrame,
    PipelineConfig,
    RealtimeAIProviderBridge,
    SignalWireMediaInput,
    build_pipeline,
    media_bytes_to_audio_frame,
    provider_frame_to_persona_frame,
)
from opencloser.runtime.pipecat.provider import (
    AudioChunk,
    ExtractionEvent,
    ProviderSessionHandle,
    TranscriptSegment,
)
from opencloser.runtime.pipecat.provider_fake import FakeRealtimeAIProvider

# ---------------------------------------------------------------------------
# Config (research.md §5: μ-law 8 kHz, 800 ms VAD fallback)
# ---------------------------------------------------------------------------


def test_pipeline_config_defaults() -> None:
    cfg = PipelineConfig()
    assert cfg.audio_encoding == AUDIO_ENCODING == "mulaw"
    assert cfg.sample_rate_hz == SAMPLE_RATE_HZ == 8000
    assert cfg.num_channels == 1
    assert cfg.vad_silence_ms == VAD_SILENCE_MS == 800


# ---------------------------------------------------------------------------
# media_bytes_to_audio_frame
# ---------------------------------------------------------------------------


def test_media_bytes_to_audio_frame() -> None:
    chunk = b"\x00\x01" * 80
    frame = media_bytes_to_audio_frame(chunk, PipelineConfig())
    assert isinstance(frame, InputAudioRawFrame)
    assert frame.audio == chunk
    assert frame.sample_rate == 8000
    assert frame.num_channels == 1


# ---------------------------------------------------------------------------
# provider_frame_to_persona_frame
# ---------------------------------------------------------------------------


def test_translate_transcript_segment() -> None:
    seg = TranscriptSegment(text="hello", speaker="persona")
    frame = provider_frame_to_persona_frame(seg)
    assert isinstance(frame, PersonaTranscriptFrame)
    assert frame.segment is seg


def test_translate_extraction_event() -> None:
    ev = ExtractionEvent(field="captured_email", value="a@b.test")
    frame = provider_frame_to_persona_frame(ev)
    assert isinstance(frame, PersonaExtractionFrame)
    assert frame.event is ev


def test_translate_unknown_frame_is_absorbed() -> None:
    # Provider audio (or any non-persona) frame returns None — nothing leaks to the sink.
    assert provider_frame_to_persona_frame(AudioChunk(data=b"\x00")) is None
    assert provider_frame_to_persona_frame(object()) is None


# ---------------------------------------------------------------------------
# build_pipeline assembly
# ---------------------------------------------------------------------------


def test_build_pipeline_assembles_three_stages() -> None:
    built = build_pipeline(
        provider=FakeRealtimeAIProvider(),
        handle=ProviderSessionHandle(session_id="sess-t029"),
    )
    assert isinstance(built.pipeline, Pipeline)
    assert isinstance(built.media_input, SignalWireMediaInput)
    assert isinstance(built.bridge, RealtimeAIProviderBridge)
    assert isinstance(built.sink, PersonaSink)
    # The runtime reads collected persona frames from the sink (starts empty).
    assert built.sink.collected == []


def test_build_pipeline_accepts_custom_config() -> None:
    cfg = PipelineConfig(sample_rate_hz=16000)
    built = build_pipeline(
        provider=FakeRealtimeAIProvider(),
        handle=ProviderSessionHandle(session_id="sess-t029b"),
        config=cfg,
    )
    assert built.media_input._config.sample_rate_hz == 16000
