"""Dataverse OAuth2 authentication — Slice 2 (research.md §2).

Acquires an access token via the OAuth2 client-credentials grant against Microsoft
Entra ID and caches it in-process for the run lifetime. Secrets come from
``DataverseSecrets`` (loaded from environment variables — spec FR-005).
"""

from __future__ import annotations

import time

import httpx

from opencloser.crm.dataverse.errors import raise_for_dataverse_response, wrap_transport_error
from opencloser.models import DataverseSecrets

_TOKEN_ENDPOINT = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"

# Refresh slightly before the true expiry so a request never races token expiry.
_EXPIRY_SKEW_SECONDS = 60.0

# Fallback token lifetime when the response omits `expires_in`.
_DEFAULT_EXPIRES_IN = 3600.0


class DataverseTokenProvider:
    """Acquires and in-process-caches a Dataverse access token (client-credentials grant)."""

    def __init__(self, secrets: DataverseSecrets, *, http: httpx.Client | None = None) -> None:
        self._secrets = secrets
        self._http = http if http is not None else httpx.Client(timeout=30.0)
        self._owns_http = http is None
        self._token: str | None = None
        self._expires_at: float = 0.0

    def token(self, *, now: float | None = None) -> str:
        """Return a valid access token, acquiring a fresh one when the cache is empty
        or within the expiry skew window. ``now`` (monotonic seconds) is injectable
        for tests."""
        clock = time.monotonic() if now is None else now
        if self._token is None or clock >= self._expires_at:
            self._acquire(clock)
        assert self._token is not None  # set by _acquire
        return self._token

    def _acquire(self, clock: float) -> None:
        endpoint = _TOKEN_ENDPOINT.format(tenant=self._secrets.tenant_id)
        form = {
            "grant_type": "client_credentials",
            "client_id": self._secrets.client_id,
            "client_secret": self._secrets.client_secret,
            "scope": self._secrets.env_url.rstrip("/") + "/.default",
        }
        try:
            response = self._http.post(endpoint, data=form)
        except httpx.HTTPError as exc:
            raise wrap_transport_error(exc) from exc
        raise_for_dataverse_response(response)
        body = response.json()
        self._token = body["access_token"]
        lifetime = float(body.get("expires_in", _DEFAULT_EXPIRES_IN))
        self._expires_at = clock + lifetime - _EXPIRY_SKEW_SECONDS

    def close(self) -> None:
        """Close the owned httpx client (no-op when an external client was injected)."""
        if self._owns_http:
            self._http.close()
