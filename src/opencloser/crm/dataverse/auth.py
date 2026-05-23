"""Dataverse OAuth2 authentication — Slice 2 (research.md §2).

Acquires an access token via the OAuth2 client-credentials grant against Microsoft
Entra ID and caches it in-process for the run lifetime. Secrets come from
``DataverseSecrets`` (loaded from environment variables — spec FR-005).
"""

from __future__ import annotations

import time

import httpx

from opencloser.crm.dataverse.errors import (
    DataverseError,
    PermanentDataverseError,
    TransientDataverseError,
    _parse_retry_after,
    is_transient_status,
)
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
            raise _wrap_auth_transport_error(exc, endpoint) from exc
        if not response.is_success:
            raise _auth_status_error(response, endpoint)
        try:
            body = response.json()
            access_token = body["access_token"]
        except (ValueError, KeyError, TypeError) as exc:
            # A 2xx without a usable `access_token` is an Entra ID protocol/config
            # error — surface it as permanent so operators see the auth source instead
            # of a bare JSON/KeyError traceback. The body is NOT echoed: token-endpoint
            # diagnostics may include request echoes (Copilot review on PR #3).
            raise PermanentDataverseError(
                f"Entra ID token endpoint returned a 2xx response without a usable "
                f"`access_token` field ({type(exc).__name__})"
            ) from exc
        # Reject null / empty / non-string access_token — otherwise the cached value
        # is unusable and downstream Authorization headers will fail in confusing ways
        # (Codex review on PR #3).
        if not isinstance(access_token, str) or not access_token:
            raise PermanentDataverseError(
                "Entra ID token endpoint returned an empty or non-string "
                "`access_token` field"
            )
        # `expires_in` may be missing, null, non-numeric, or otherwise unparseable —
        # treat any parse failure as a permanent auth-payload error rather than letting
        # a raw ValueError/TypeError escape (Codex review on PR #3).
        raw_expires = body.get("expires_in", _DEFAULT_EXPIRES_IN)
        try:
            lifetime = float(raw_expires)
        except (TypeError, ValueError) as exc:
            raise PermanentDataverseError(
                "Entra ID token endpoint returned a non-numeric `expires_in` value"
            ) from exc
        self._token = access_token
        self._expires_at = clock + lifetime - _EXPIRY_SKEW_SECONDS

    def close(self) -> None:
        """Close the owned httpx client (no-op when an external client was injected)."""
        if self._owns_http:
            self._http.close()


# Auth-aware error wrappers — keep the Entra ID/OAuth source visible in messages so
# operators don't mis-diagnose a token-endpoint outage as a Dataverse Web API outage
# (Copilot review on PR #3). The transient/permanent split mirrors
# `errors.wrap_transport_error` exactly: only timeouts and network failures are
# transient; misconfiguration-class transport errors (UnsupportedProtocol,
# ProtocolError, ProxyError) are permanent so the retry budget is not burned on
# impossible requests (Copilot follow-up review on PR #3).
def _wrap_auth_transport_error(exc: httpx.HTTPError, endpoint: str) -> DataverseError:
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
        return TransientDataverseError(
            f"Entra ID token endpoint unreachable ({endpoint}): {exc!r}"
        )
    return PermanentDataverseError(
        f"Entra ID token endpoint error ({endpoint}): {exc!r}"
    )


def _auth_status_error(response: httpx.Response, endpoint: str) -> DataverseError:
    status = response.status_code
    detail = f"Entra ID token endpoint returned HTTP {status} ({endpoint})"
    if is_transient_status(status):
        return TransientDataverseError(
            detail,
            retry_after=_parse_retry_after(response.headers.get("Retry-After")),
            status_code=status,
        )
    return PermanentDataverseError(detail, status_code=status)
