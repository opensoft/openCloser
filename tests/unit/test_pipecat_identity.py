"""T027 — unit tests for the Pipecat runtime identity recorder (identity.py).

Covers FR-016 (record ``{runtime_name, runtime_version, provider_name,
model_name, model_version}`` on every session) and FR-035 (no credentials).
"""

from __future__ import annotations

import pytest

from opencloser.models import RealtimeProviderSession
from opencloser.runtime.pipecat.identity import (
    RUNTIME_NAME,
    build_runtime_identity,
    pipecat_runtime_version,
)
from tests.fixtures.pipecat import FakeRealtimeAIProvider

_SECRET = "T027-API-KEY-must-never-be-recorded"


class _LeakyProvider:
    """A provider whose identity dict leaks a credential-bearing key (FR-035)."""

    @property
    def identity(self) -> dict[str, str]:
        return {
            "provider_name": "fake-realtime",
            "model_name": "fake-realtime-1",
            "model_version": "test-0.1",
            "api_key": _SECRET,
        }


class _IncompleteProvider:
    """A provider whose identity is missing a required FR-016 field."""

    @property
    def identity(self) -> dict[str, str]:
        return {"provider_name": "fake-realtime", "model_name": "fake-realtime-1"}


def test_pipecat_runtime_version_is_nonempty() -> None:
    v = pipecat_runtime_version()
    assert isinstance(v, str) and v


def test_build_runtime_identity_records_all_fr016_fields() -> None:
    identity = build_runtime_identity(FakeRealtimeAIProvider())
    assert isinstance(identity, RealtimeProviderSession)
    assert identity.runtime_name == RUNTIME_NAME == "pipecat"
    assert identity.runtime_version  # the installed pipecat-ai version
    assert identity.provider_name == "fake-realtime"
    assert identity.model_name == "fake-realtime-1"
    assert identity.model_version == "test-0.1"


def test_build_runtime_identity_accepts_runtime_version_override() -> None:
    identity = build_runtime_identity(FakeRealtimeAIProvider(), runtime_version="9.9.9-test")
    assert identity.runtime_version == "9.9.9-test"


def test_build_runtime_identity_rejects_credential_key() -> None:
    with pytest.raises(ValueError, match="FR-035"):
        build_runtime_identity(_LeakyProvider())


def test_build_runtime_identity_no_credential_in_serialized_record() -> None:
    """Even from a clean provider, the serialized identity carries no secret."""
    identity = build_runtime_identity(FakeRealtimeAIProvider())
    assert _SECRET not in identity.model_dump_json()


def test_build_runtime_identity_rejects_missing_required_field() -> None:
    with pytest.raises(ValueError, match="missing required FR-016 field"):
        build_runtime_identity(_IncompleteProvider())
