"""Dataverse error taxonomy + small OData helpers — Slice 2 (spec §Definitions,
FR-023).

`TransientDataverseError` is retryable within the bounded retry budget;
`PermanentDataverseError` MUST NOT be retried. Classification of HTTP responses and
httpx transport exceptions follows the spec's Definitions section exactly.
"""

from __future__ import annotations

import re

import httpx


def odata_string_literal(value: str) -> str:
    """Quote a string for use as an OData v4 literal in `$filter` clauses.

    Per OData v4 spec (section 5.1.1.6.1), a single quote inside a string
    literal is escaped by doubling it (`'` -> `''`). Centralizing the
    escape here keeps every `$filter` clause that interpolates a string
    safe by construction — no caller has to remember to escape, and the
    door for OData-filter injection via user-supplied values stays shut.

    Returns the value wrapped in single quotes with embedded `'` doubled.
    """
    return "'" + value.replace("'", "''") + "'"


# OData `Edm.Guid` literal pattern: unquoted in `$filter` (Dataverse) and
# expected to match a strict alphanumeric-with-dashes shape. Pass 2A
# (2026-05-24 audit-remediation) — adapter call sites that interpolate
# primary-id / owner-id values raw into $filter clauses route through this
# helper for defense-in-depth, mirroring `queue_loader._odata_token`.
_GUID_LITERAL_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def odata_guid_literal(value: object) -> str:
    """Return ``value`` as an unquoted OData GUID literal after validating it
    matches a safe alphanumeric-with-dashes/underscores shape. Raises
    ``ValueError`` for anything else — including the OData reserved
    characters (`'`, ` `, `,`, `)`, ...) that could corrupt a `$filter` or
    open an injection vector.

    The validator is intentionally permissive enough to accept real
    Dataverse GUIDs (`00000000-0000-0000-0000-000000000000`) and the test
    fixture's shorthand IDs (`q-contract-0001`) while still rejecting
    anything that could break the surrounding `$filter` syntax.
    """
    text = str(value)
    if not _GUID_LITERAL_RE.fullmatch(text):
        raise ValueError(
            f"unsafe OData GUID literal {value!r} — must match [A-Za-z0-9_-]+"
        )
    return text


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
    # Strip BOTH the host AND the query string from the URL. Per spec §FR-005 +
    # the T047 secret-redaction contract, `DATAVERSE_ENV_URL` is a secret value
    # that MUST NOT land in `last_error` / CrmRunReport.message / stdout. The
    # query string also routinely carries session IDs, campaign GUIDs, or record
    # GUIDs that we do not want to echo into operator logs (Copilot review on
    # PR #3). The URL PATH alone is diagnostic enough — the operator knows which
    # environment they configured. The `<env>` placeholder makes the redaction
    # visible at a glance.
    safe_path = response.request.url.path
    detail = (
        f"Dataverse returned HTTP {status} for "
        f"{response.request.method} <env>{safe_path}"
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

    Only network-recoverable exceptions are transient — timeouts and connection /
    read / write / close errors. Misconfiguration-class transport errors —
    `UnsupportedProtocol`, `ProtocolError`, `ProxyError`, and anything outside
    `TransportError` — are permanent: retrying them would burn the FR-023 retry
    budget on a request that cannot succeed (Codex review on PR #3, rule python:S5773
    in spirit).
    """
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
        return TransientDataverseError(f"Dataverse transport failure: {exc!r}")
    return PermanentDataverseError(f"Dataverse error: {exc!r}")
