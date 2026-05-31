"""T022 — focused unit tests for ``transport/signalwire/signature.py``.

Per pyproject markers convention, this is a per-module unit test that
exercises ``verify_signature`` in isolation. The end-to-end propagation
through ``SignalWireTransport.ingest_callback`` is covered by T013's
signature tests (which will turn green when T025 wires this function into
``ingest_callback``).
"""

from __future__ import annotations

import base64
import hashlib
import hmac

import pytest

from opencloser.transport.signalwire.errors import SignatureVerificationError
from opencloser.transport.signalwire.signature import (
    SIGNATURE_HEADER_CANDIDATES,
    verify_signature,
)

pytestmark = pytest.mark.module("transport")


_SECRET = "T022-FAKE-SIGNING-SECRET-must-never-appear-in-logs"
_BODY = b'{"CallSid":"CA-T022-001","CallStatus":"completed"}'


def _valid_signature() -> str:
    """Compute the SignalWire-style signature for ``_BODY`` keyed by ``_SECRET``."""
    mac = hmac.new(_SECRET.encode("utf-8"), msg=_BODY, digestmod=hashlib.sha256)
    return base64.b64encode(mac.digest()).decode("ascii")


def test_valid_signature_does_not_raise() -> None:
    """A correctly-computed HMAC-SHA256 signature is accepted."""
    headers = {"X-SignalWire-Signature": _valid_signature()}
    # No exception → success.
    verify_signature(headers=headers, body=_BODY, signing_secret=_SECRET)


def test_lowercase_header_is_accepted() -> None:
    """ASGI / receiver code often lower-cases headers; both forms work."""
    headers = {"x-signalwire-signature": _valid_signature()}
    verify_signature(headers=headers, body=_BODY, signing_secret=_SECRET)


def test_bad_signature_raises() -> None:
    """A forged signature header raises ``SignatureVerificationError``."""
    headers = {"X-SignalWire-Signature": "not-a-real-hmac"}
    with pytest.raises(SignatureVerificationError) as exc_info:
        verify_signature(headers=headers, body=_BODY, signing_secret=_SECRET)
    assert exc_info.value.http_status == 401


def test_missing_signature_header_raises() -> None:
    """Absent signature header → ``SignatureVerificationError`` with 401."""
    with pytest.raises(SignatureVerificationError) as exc_info:
        verify_signature(headers={}, body=_BODY, signing_secret=_SECRET)
    assert exc_info.value.http_status == 401


def test_empty_signature_header_raises() -> None:
    """Empty signature header value MUST be treated as missing."""
    headers = {"X-SignalWire-Signature": ""}
    with pytest.raises(SignatureVerificationError):
        verify_signature(headers=headers, body=_BODY, signing_secret=_SECRET)


def test_body_tampering_is_detected() -> None:
    """A signature computed against a different body MUST be rejected."""
    other_body = b'{"CallSid":"CA-T022-EVIL","CallStatus":"completed"}'
    # Sign the OTHER body, then submit `_BODY` — signature mismatch.
    signature_for_other = base64.b64encode(
        hmac.new(_SECRET.encode("utf-8"), msg=other_body, digestmod=hashlib.sha256).digest()
    ).decode("ascii")
    headers = {"X-SignalWire-Signature": signature_for_other}
    with pytest.raises(SignatureVerificationError):
        verify_signature(headers=headers, body=_BODY, signing_secret=_SECRET)


def test_wrong_secret_is_detected() -> None:
    """A signature computed with a different secret MUST be rejected."""
    other_secret = "different-secret"
    signature_with_wrong_key = base64.b64encode(
        hmac.new(other_secret.encode("utf-8"), msg=_BODY, digestmod=hashlib.sha256).digest()
    ).decode("ascii")
    headers = {"X-SignalWire-Signature": signature_with_wrong_key}
    with pytest.raises(SignatureVerificationError):
        verify_signature(headers=headers, body=_BODY, signing_secret=_SECRET)


def test_exception_does_not_carry_secret_or_body() -> None:
    """The exception message MUST NOT echo the signing secret or the body
    (FR-008 / FR-035 / Round 2 Q9 — no reflected-payload leakage)."""
    headers = {"X-SignalWire-Signature": "wrong"}
    with pytest.raises(SignatureVerificationError) as exc_info:
        verify_signature(headers=headers, body=_BODY, signing_secret=_SECRET)
    message = str(exc_info.value)
    assert _SECRET not in message, "exception leaked signing secret"
    assert _BODY.decode("utf-8") not in message, "exception leaked callback body"


def test_signature_header_candidates_documented() -> None:
    """Pin the accepted header-name list so silent additions get reviewed."""
    assert SIGNATURE_HEADER_CANDIDATES == (
        "X-SignalWire-Signature",
        "x-signalwire-signature",
    )
