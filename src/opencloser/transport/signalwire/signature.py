"""SignalWire HMAC-SHA256 signature verification (FR-008, research.md §2).

Verifies the SignalWire-supplied HMAC signature header on every inbound
callback before any orchestrator hand-off. A failed-signature callback is
rejected with HTTP 401 by raising :class:`SignatureVerificationError`; the
caller (the SignalWire callback receiver in real-call mode, or the
``SignalWireTransport.ingest_callback`` test entrypoint) is responsible for
also recording the rejection in the distinct ``RejectedAuthCallbackLog``
audit log per Round 2 Q9 (T032 implements the writer).

This module MUST NOT log the signing secret and MUST NOT log the callback
body content (FR-008 / Round 2 Q9 — defense in depth against
reflected-payload leakage).
"""

from __future__ import annotations

import base64
import hashlib
import hmac

from opencloser.transport.signalwire.errors import SignatureVerificationError

# The SignalWire signature header. Per SignalWire's documented webhook
# signature mechanism the header carries the base64-encoded HMAC-SHA256 of
# the request body computed with the shared signing secret. We accept both
# canonical and lowercase header keys so a header-normalizing receiver
# (e.g. an ASGI application) does not need a special case.
SIGNATURE_HEADER_CANDIDATES: tuple[str, ...] = (
    "X-SignalWire-Signature",
    "x-signalwire-signature",
)


def verify_signature(
    *,
    headers: dict[str, str],
    body: bytes,
    signing_secret: str,
) -> None:
    """Verify the SignalWire-supplied HMAC signature on an inbound callback.

    :raises SignatureVerificationError: when the signature header is missing,
        empty, or does not match the HMAC-SHA256 of ``body`` computed with
        ``signing_secret``. The exception is intentionally generic — its
        message does NOT include the secret, the expected/actual signature
        values, or the body content.
    """

    provided = _extract_signature_header(headers)
    if not provided:
        # Generic message — must NOT echo the body or the secret. The header
        # name is fine to surface for operator triage.
        raise SignatureVerificationError(
            "missing SignalWire signature header"
        )

    expected = _compute_expected_signature(body=body, signing_secret=signing_secret)
    # ``hmac.compare_digest`` is constant-time; protects against timing
    # side-channels per FR-008 / OWASP recommended practice.
    if not hmac.compare_digest(provided, expected):
        raise SignatureVerificationError("SignalWire signature mismatch")


def _extract_signature_header(headers: dict[str, str]) -> str:
    """Return the signature header value, or an empty string if absent.

    Tries each candidate in :data:`SIGNATURE_HEADER_CANDIDATES`. ASGI /
    receiver code often lower-cases headers; accept both forms so the caller
    does not need a normalization shim.
    """
    for candidate in SIGNATURE_HEADER_CANDIDATES:
        value = headers.get(candidate)
        if value:
            return value
    return ""


def _compute_expected_signature(*, body: bytes, signing_secret: str) -> str:
    """Compute the base64-encoded HMAC-SHA256 of ``body`` keyed by
    ``signing_secret``. Returns the canonical string form ready for
    constant-time comparison against the header value.
    """
    mac = hmac.new(
        signing_secret.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256,
    )
    return base64.b64encode(mac.digest()).decode("ascii")
