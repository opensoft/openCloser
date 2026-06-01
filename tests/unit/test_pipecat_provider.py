"""T028 — unit tests for the real-time AI provider surface (provider.py +
provider_fake.py) per research.md §3.

Covers the vendor-neutral frame types, the ``SLICE3_REALTIME_PROVIDER``
selection seam, and the in-tree CI fake's 3-method contract + FR-035 identity.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from opencloser.runtime.pipecat.identity import build_runtime_identity
from opencloser.runtime.pipecat.provider import (
    DISABLED_PROVIDER_NAME,
    FAKE_PROVIDER_NAME,
    AudioChunk,
    ExtractionEvent,
    ProviderDisabledError,
    ProviderSessionHandle,
    TranscriptSegment,
    select_realtime_provider,
)
from opencloser.runtime.pipecat.provider_fake import FakeRealtimeAIProvider

# ---------------------------------------------------------------------------
# Frame types + handle
# ---------------------------------------------------------------------------


def test_frame_types_construct() -> None:
    seg = TranscriptSegment(text="hello", speaker="persona")
    assert seg.text == "hello" and seg.speaker == "persona"
    assert TranscriptSegment(text="hi").speaker == "caller"  # default
    ev = ExtractionEvent(field="captured_email", value="a@b.test")
    assert ev.field == "captured_email" and ev.value == "a@b.test" and ev.confidence == 1.0
    assert AudioChunk(data=b"\x00\x01").data == b"\x00\x01"


def test_provider_session_handle_exposes_session_id() -> None:
    assert ProviderSessionHandle(session_id="sess-1").session_id == "sess-1"


# ---------------------------------------------------------------------------
# select_realtime_provider
# ---------------------------------------------------------------------------


def test_select_provider_defaults_to_fake_when_unset() -> None:
    provider = select_realtime_provider(env={})
    assert isinstance(provider, FakeRealtimeAIProvider)


def test_select_provider_explicit_fake() -> None:
    provider = select_realtime_provider(env={"SLICE3_REALTIME_PROVIDER": FAKE_PROVIDER_NAME})
    assert isinstance(provider, FakeRealtimeAIProvider)


def test_select_provider_unknown_raises() -> None:
    with pytest.raises(ValueError, match="unknown SLICE3_REALTIME_PROVIDER"):
        select_realtime_provider(env={"SLICE3_REALTIME_PROVIDER": "some-real-provider"})


def test_select_provider_disabled_raises_distinct_error() -> None:
    """The config-sanctioned ``"disabled"`` value (config/slice3.toml) raises a
    distinct ``ProviderDisabledError`` — NOT the unknown-provider ValueError —
    so the US3 readiness gate can map it to "real-call unavailable"."""
    with pytest.raises(ProviderDisabledError, match="rehearsal-only"):
        select_realtime_provider(env={"SLICE3_REALTIME_PROVIDER": DISABLED_PROVIDER_NAME})
    # And it is not mistaken for a generic misconfiguration.
    assert not issubclass(ProviderDisabledError, ValueError)


# ---------------------------------------------------------------------------
# FakeRealtimeAIProvider — 3-method contract
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fake_provider_session_lifecycle_and_replay() -> None:
    frames = [
        TranscriptSegment(text="Hi, this is an AI assistant.", speaker="persona"),
        ExtractionEvent(field="intent_classification", value="interested"),
    ]
    provider = FakeRealtimeAIProvider(scripted_frames=frames)
    assert provider.started is False and provider.ended is False

    handle = await provider.start_session(SimpleNamespace(session_id="sess-t028"))
    assert isinstance(handle, ProviderSessionHandle)
    assert handle.session_id == "sess-t028"
    assert provider.started is True

    streamed = [frame async for frame in await provider.stream_audio(handle, b"\x00" * 160)]
    assert streamed == frames

    await provider.end_session(handle)
    assert provider.ended is True


def test_fake_provider_identity_has_no_credentials() -> None:
    identity = FakeRealtimeAIProvider().identity
    assert set(identity) == {"provider_name", "model_name", "model_version"}
    # Integrates with the T027 recorder into a clean RealtimeProviderSession.
    recorded = build_runtime_identity(FakeRealtimeAIProvider())
    assert recorded.provider_name == "fake-realtime"
    assert recorded.runtime_name == "pipecat"
