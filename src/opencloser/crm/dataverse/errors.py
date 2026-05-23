"""Dataverse error taxonomy — Slice 2 (spec §Definitions, FR-023).

`TransientDataverseError` is retryable within the bounded retry budget;
`PermanentDataverseError` MUST NOT be retried. Classification of HTTP responses and
httpx transport exceptions follows the spec's Definitions section exactly.
"""

from __future__ import annotations

import httpx

# HTTP status codes treated as transient (spec §Definitions §"Transient Dataverse error":
# network timeout, connection reset, HTTP 408, HTTP 429, or HTTP 5xx).
_TRANSIENT_FIXED_STATUS = frozenset({408, 429})


class DataverseError(Exception):
    """Base class for every Dataverse access failure."""


class TransientDataverseError(DataverseError):
    """A retryable Dataverse failure — network timeout, connection reset, or HTTP 408/429/5xx.

    `retry_after` carries the server's Retry-After hint in seconds when present (HTTP 429);
    the client caps it per FR-023. `status_code` is the HTTP status when the error came
    from a response (None for transport-level failures).
    """

    def __init__(
        self,
        message: str,
        *,
        retry_after: float | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_after = retry_after
        self.status_code = status_code


class PermanentDataverseError(DataverseError):
    """A non-retryable Dataverse failure — HTTP 400/401/403/404, option-set mismatch,
    missing required mapping, metadata drift, or invalid/missing credentials.

    `status_code` is the HTTP status when the error came from a response (None for
    non-HTTP failures). Callers MAY narrow handling by status (e.g., treat 404 as
    "entity missing" while letting 401/403 propagate).
    """

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def is_transient_status(status_code: int) -> bool:
    """True when an HTTP status is transient per spec §Definitions (408, 429, or 5xx)."""
    return status_code in _TRANSIENT_FIXED_STATUS or 500 <= status_code <= 599


def _parse_retry_after(value: str | None) -> float | None:
    """Parse a Retry-After header (delta-seconds form) to non-negative float seconds."""
    if value is None:
        return None
    try:
        seconds = float(value)
    except ValueError:
        return None
    return seconds if seconds >= 0 else None


def raise_for_dataverse_response(response: httpx.Response) -> None:
    """Raise the typed Dataverse error for a non-2xx response; return quietly on 2xx.

    Transient vs. permanent classification follows spec §Definitions.
    """
    if response.is_success:
        return
    status = response.status_code
    detail = (
        f"Dataverse returned HTTP {status} for "
        f"{response.request.method} {response.request.url}"
    )
    if is_transient_status(status):
        raise TransientDataverseError(
            detail,
            retry_after=_parse_retry_after(response.headers.get("Retry-After")),
            status_code=status,
        )
    raise PermanentDataverseError(detail, status_code=status)


def wrap_transport_error(exc: httpx.HTTPError) -> DataverseError:
    """Map an httpx transport-level exception to the typed Dataverse error.

    Timeouts and connection/network/transport errors are transient (httpx models
    `TimeoutException` as a subclass of `TransportError`); anything else is permanent.
    """
    if isinstance(exc, httpx.TransportError):
        return TransientDataverseError(f"Dataverse transport failure: {exc!r}")
    return PermanentDataverseError(f"Dataverse error: {exc!r}")
