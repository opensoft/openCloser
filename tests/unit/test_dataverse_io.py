"""Unit tests for the Slice 2 Dataverse I/O layer — OAuth2 auth, the Web API client
with bounded transient retry, and the mapping translator (tasks T010-T012; part of T016).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from opencloser.crm.dataverse import errors
from opencloser.crm.dataverse.auth import DataverseTokenProvider
from opencloser.crm.dataverse.client import DataverseClient
from opencloser.crm.dataverse.mapping import MappingError, MappingTranslator, load_mapping
from opencloser.models import DataverseSecrets, RetryConfig

_REPO_ROOT = Path(__file__).parents[2]
_MAPPING_FIXTURE = _REPO_ROOT / "tests/fixtures/dataverse/dataverse_mapping.json"

_SECRETS = DataverseSecrets(
    tenant_id="tenant-1",
    client_id="client-1",
    client_secret="secret-1",
    env_url="https://fake.crm.dynamics.com",
)


def _retry() -> RetryConfig:
    return RetryConfig(max_retries=3, backoff_seconds=[1.0, 2.0, 4.0], retry_after_cap_seconds=30.0)


def _mock_client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


# ---------------------------------------------------------------------------
# T010 — OAuth2 client-credentials auth
# ---------------------------------------------------------------------------


def test_token_acquired_and_cached() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(
            200, json={"access_token": "tok-A", "expires_in": 3600}, request=request
        )

    provider = DataverseTokenProvider(_SECRETS, http=_mock_client(handler))
    assert provider.token(now=0.0) == "tok-A"
    assert provider.token(now=120.0) == "tok-A"
    assert calls["n"] == 1  # cached — one acquisition


def test_token_refreshed_after_expiry() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(
            200, json={"access_token": f"tok-{calls['n']}", "expires_in": 100}, request=request
        )

    provider = DataverseTokenProvider(_SECRETS, http=_mock_client(handler))
    assert provider.token(now=0.0) == "tok-1"  # expires_at = 0 + 100 - 60 skew = 40
    assert provider.token(now=50.0) == "tok-2"  # 50 >= 40 -> refreshed
    assert calls["n"] == 2


def test_token_transient_failure_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, request=request)

    provider = DataverseTokenProvider(_SECRETS, http=_mock_client(handler))
    with pytest.raises(errors.TransientDataverseError):
        provider.token(now=0.0)


# ---------------------------------------------------------------------------
# T011 — Web API client with bounded transient retry
# ---------------------------------------------------------------------------


class _StubToken:
    """A token provider stub — keeps client retry tests independent of the auth path."""

    def token(self) -> str:
        return "test-token"


def _status_handler(
    statuses: list[int], headers: dict[int, dict[str, str]] | None = None
) -> tuple[Callable[[httpx.Request], httpx.Response], dict[str, int]]:
    """A MockTransport handler that yields `statuses` in order (repeating the last)."""
    calls = {"n": 0}
    per_call_headers = headers or {}

    def handler(request: httpx.Request) -> httpx.Response:
        i = calls["n"]
        calls["n"] += 1
        status = statuses[i] if i < len(statuses) else statuses[-1]
        if status == 200:
            return httpx.Response(200, json={"value": []}, request=request)
        return httpx.Response(status, headers=per_call_headers.get(i, {}), request=request)

    return handler, calls


def _client(
    handler: Callable[[httpx.Request], httpx.Response], sleeps: list[float]
) -> DataverseClient:
    return DataverseClient(
        _SECRETS.env_url, _StubToken(), _retry(), http=_mock_client(handler), sleep=sleeps.append
    )


def test_client_retries_transient_status_then_succeeds() -> None:
    handler, calls = _status_handler([503, 503, 200])
    sleeps: list[float] = []
    response = _client(handler, sleeps).get("accounts")
    assert response.status_code == 200
    assert calls["n"] == 3
    assert sleeps == [1.0, 2.0]


def test_client_permanent_error_not_retried() -> None:
    handler, calls = _status_handler([404])
    sleeps: list[float] = []
    with pytest.raises(errors.PermanentDataverseError):
        _client(handler, sleeps).get("accounts")
    assert calls["n"] == 1
    assert sleeps == []


def test_client_exhausts_retry_budget() -> None:
    handler, calls = _status_handler([503])
    sleeps: list[float] = []
    with pytest.raises(errors.TransientDataverseError):
        _client(handler, sleeps).get("accounts")
    assert calls["n"] == 4  # initial attempt + 3 retries (FR-023)
    assert sleeps == [1.0, 2.0, 4.0]


def test_client_caps_retry_after() -> None:
    handler, _ = _status_handler([429, 200], headers={0: {"Retry-After": "999"}})
    sleeps: list[float] = []
    _client(handler, sleeps).get("accounts")
    assert sleeps == [30.0]  # server's 999s Retry-After capped at retry_after_cap_seconds


def test_client_retries_transport_error() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] <= 2:
            raise httpx.ConnectError("connection refused")
        return httpx.Response(200, json={"value": []}, request=request)

    sleeps: list[float] = []
    response = _client(handler, sleeps).get("accounts")
    assert response.status_code == 200
    assert calls["n"] == 3
    assert sleeps == [1.0, 2.0]


def test_client_delay_with_empty_backoff_uses_zero() -> None:
    """`RetryConfig.backoff_seconds == []` -> retries happen immediately (delay 0).
    (Sourcery suggestion — lock in the empty-backoff semantics.)"""
    handler, _ = _status_handler([503, 200])
    sleeps: list[float] = []
    retry = RetryConfig(max_retries=1, backoff_seconds=[], retry_after_cap_seconds=30.0)
    client = DataverseClient(
        _SECRETS.env_url, _StubToken(), retry,
        http=_mock_client(handler), sleep=sleeps.append,
    )
    client.get("accounts")
    assert sleeps == [0.0]


def test_client_delay_with_short_backoff_repeats_last_value() -> None:
    """A backoff list shorter than `max_retries` reuses the last value for the
    remaining retries. (Sourcery suggestion — lock in the short-backoff semantics.)"""
    handler, _ = _status_handler([503, 503, 503, 200])
    sleeps: list[float] = []
    retry = RetryConfig(max_retries=3, backoff_seconds=[1.5], retry_after_cap_seconds=30.0)
    client = DataverseClient(
        _SECRETS.env_url, _StubToken(), retry,
        http=_mock_client(handler), sleep=sleeps.append,
    )
    client.get("accounts")
    assert sleeps == [1.5, 1.5, 1.5]


def test_client_post_and_patch() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.method)
        return httpx.Response(204, request=request)

    client = _client(handler, [])
    assert client.post("phonecalls", json={"x": 1}).status_code == 204
    assert client.patch("medx_callqueueitems(1)", json={"y": 2}).status_code == 204
    assert seen == ["POST", "PATCH"]


# ---------------------------------------------------------------------------
# T012 — mapping loader + translator
# ---------------------------------------------------------------------------


def test_load_mapping_and_translate() -> None:
    translator = MappingTranslator(load_mapping(_MAPPING_FIXTURE))
    assert translator.is_approved() is True
    assert translator.entity_logical_name("queue_item") == "medx_callqueueitem"
    assert translator.logical_name("queue.status") == "medx_callstatus"
    assert translator.option_set_value("queue_status.ready") == 0
    assert translator.option_set_key_for_value("queue.status", 0) == "queue_status.ready"
    assert translator.option_set_key_for_value("queue.status", 99) is None


def test_mapping_approved_update_fields() -> None:
    translator = MappingTranslator(load_mapping(_MAPPING_FIXTURE))
    approved = translator.approved_update_logical_names()
    assert "medx_callstatus" in approved
    assert "medx_phonenumber" not in approved  # phone is read, never an approved update field
    assert "medx_notes" in translator.preserve_if_present()


def test_load_mapping_missing_file(tmp_path: Path) -> None:
    with pytest.raises(MappingError, match="not found"):
        load_mapping(tmp_path / "nope.json")


def test_load_mapping_invalid_json(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(MappingError, match="not valid JSON"):
        load_mapping(bad)


def test_translator_unknown_field_raises() -> None:
    translator = MappingTranslator(load_mapping(_MAPPING_FIXTURE))
    with pytest.raises(MappingError, match="no Dataverse field mapping"):
        translator.logical_name("queue.nonexistent")
