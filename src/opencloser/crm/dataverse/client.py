"""Dataverse Web API client — Slice 2 (research.md §1, FR-023).

A thin httpx wrapper over the Dataverse Web API (OData v4) with bounded transient
retry: the initial attempt plus ``RetryConfig.max_retries`` retries, fixed backoff,
and a capped ``Retry-After``. Transient failures are retried; permanent failures
(spec §Definitions) raise immediately.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, Protocol

import httpx

from opencloser.crm.dataverse.errors import (
    PermanentDataverseError,
    TransientDataverseError,
    raise_for_dataverse_response,
    wrap_transport_error,
)
from opencloser.models import RetryConfig

# Dataverse Web API v9.2 base path (research.md §1).
_API_PATH = "/api/data/v9.2/"


class TokenProvider(Protocol):
    """Structural type for the auth dependency — see ``auth.DataverseTokenProvider``."""

    def token(self) -> str:  # pragma: no cover - protocol
        ...


class DataverseClient:
    """Dataverse Web API client with bounded transient retry (FR-023)."""

    def __init__(
        self,
        env_url: str,
        token_provider: TokenProvider,
        retry: RetryConfig,
        *,
        http: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._base = env_url.rstrip("/") + _API_PATH
        self._token_provider = token_provider
        self._retry = retry
        self._http = http if http is not None else httpx.Client(timeout=30.0)
        self._owns_http = http is None
        self._sleep = sleep

    def _headers(self, extra: dict[str, str] | None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._token_provider.token()}",
            "Accept": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
        }
        if extra:
            headers.update(extra)
        return headers

    def _delay(self, attempt: int, err: TransientDataverseError) -> float:
        """Backoff before the next retry — a capped ``Retry-After`` when the server
        supplied one, otherwise the fixed per-attempt backoff (FR-023)."""
        if err.retry_after is not None:
            return min(err.retry_after, self._retry.retry_after_cap_seconds)
        backoff = self._retry.backoff_seconds
        if not backoff:
            return 0.0
        return backoff[min(attempt, len(backoff) - 1)]

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Issue one Web API request with bounded transient retry (FR-023).

        Transient failures (timeout, connection reset, HTTP 408/429/5xx) are retried up
        to ``RetryConfig.max_retries`` times; permanent failures raise immediately.
        """
        url = self._base + path.lstrip("/")
        attempts = self._retry.max_retries + 1
        for attempt in range(attempts):
            try:
                response = self._http.request(
                    method, url, json=json, params=params, headers=self._headers(headers)
                )
                raise_for_dataverse_response(response)
            except PermanentDataverseError:
                raise
            except TransientDataverseError as exc:
                if attempt + 1 >= attempts:
                    raise
                self._sleep(self._delay(attempt, exc))
                continue
            except httpx.HTTPError as exc:
                wrapped = wrap_transport_error(exc)
                if isinstance(wrapped, PermanentDataverseError) or attempt + 1 >= attempts:
                    raise wrapped from exc
                self._sleep(self._delay(attempt, wrapped))
                continue
            return response
        raise AssertionError("unreachable: retry loop exited without return or raise")  # pragma: no cover

    def get(self, path: str, *, params: dict[str, str] | None = None) -> httpx.Response:
        return self.request("GET", path, params=params)

    def post(self, path: str, *, json: Any) -> httpx.Response:
        return self.request("POST", path, json=json)

    def patch(self, path: str, *, json: Any) -> httpx.Response:
        return self.request("PATCH", path, json=json)

    def close(self) -> None:
        """Close the owned httpx client (no-op when an external client was injected)."""
        if self._owns_http:
            self._http.close()
