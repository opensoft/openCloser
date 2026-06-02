"""Unit tests for the Slice 3 live-runtime degradation detector/translator (T064)."""

from __future__ import annotations

import pytest

from opencloser.models import Disposition, HumanReviewReason
from opencloser.runtime.pipecat.degradation import (
    DEFAULT_SILENCE_AFTER_CONNECTION_TIMEOUT_SEC,
    SILENCE_TIMEOUT_ENV_VAR,
    DegradationReason,
    is_degradation_trigger,
    silence_after_connection_timeout_sec,
    translate,
)
from opencloser.runtime.pipecat.errors import (
    PipecatRuntimeError,
    RealtimeProviderError,
    SilenceAfterConnectionTimeout,
)


def _silence_exc() -> SilenceAfterConnectionTimeout:
    return SilenceAfterConnectionTimeout(session_id="s1", timeout_sec=30)


def test_is_degradation_trigger_matches_three_types() -> None:
    assert is_degradation_trigger(RealtimeProviderError("x"))
    assert is_degradation_trigger(PipecatRuntimeError("x"))
    assert is_degradation_trigger(_silence_exc())
    assert not is_degradation_trigger(ValueError("not a trigger"))


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (RealtimeProviderError("x"), DegradationReason.PROVIDER_ERROR),
        (PipecatRuntimeError("x"), DegradationReason.RUNTIME_CRASH),
        (_silence_exc(), DegradationReason.SILENCE_TIMEOUT),
    ],
)
def test_translate_post_connected_yields_script_truncated(exc, expected) -> None:
    outcome = translate(exc, connected=True)
    assert outcome.final_disposition is Disposition.NEEDS_HUMAN_REVIEW
    assert outcome.human_review_reason is HumanReviewReason.SCRIPT_TRUNCATED
    assert outcome.reason_code is expected


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (RealtimeProviderError("x"), DegradationReason.PROVIDER_ERROR),
        (PipecatRuntimeError("x"), DegradationReason.RUNTIME_CRASH),
    ],
)
def test_translate_pre_connected_yields_failed(exc, expected) -> None:
    outcome = translate(exc, connected=False)
    assert outcome.final_disposition is Disposition.FAILED
    assert outcome.human_review_reason is None
    assert outcome.reason_code is expected


def test_translate_pre_connected_silence_is_programming_error() -> None:
    with pytest.raises(ValueError, match="cannot fire pre-connection"):
        translate(_silence_exc(), connected=False)


def test_translate_rejects_non_trigger() -> None:
    with pytest.raises(TypeError, match="not an FR-013 degradation trigger"):
        translate(ValueError("nope"), connected=True)


def test_silence_timeout_default_and_constructor_fallback(monkeypatch) -> None:
    monkeypatch.delenv(SILENCE_TIMEOUT_ENV_VAR, raising=False)
    assert silence_after_connection_timeout_sec() == DEFAULT_SILENCE_AFTER_CONNECTION_TIMEOUT_SEC
    assert silence_after_connection_timeout_sec(7) == 7


def test_silence_timeout_env_override(monkeypatch) -> None:
    monkeypatch.setenv(SILENCE_TIMEOUT_ENV_VAR, "12")
    assert silence_after_connection_timeout_sec(99) == 12


@pytest.mark.parametrize("bad", ["not-an-int", "0", "-3"])
def test_silence_timeout_invalid_env_falls_back(monkeypatch, bad) -> None:
    monkeypatch.setenv(SILENCE_TIMEOUT_ENV_VAR, bad)
    # Invalid / non-positive env value is ignored in favor of the constructor default.
    assert silence_after_connection_timeout_sec(20) == 20
    monkeypatch.setenv(SILENCE_TIMEOUT_ENV_VAR, bad)
    assert (
        silence_after_connection_timeout_sec()
        == DEFAULT_SILENCE_AFTER_CONNECTION_TIMEOUT_SEC
    )
