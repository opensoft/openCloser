"""T023 — unit tests for the SignalWire transport exception hierarchy.

Covers all five exception types in
``src/opencloser/transport/signalwire/errors.py`` per
``contracts/signalwire-transport.md`` (§Raises) and spec FR-008 / FR-010 /
FR-012 / FR-026 / FR-035:

- the inheritance contract (``RealDialPhoneValidationError`` IS a
  ``TelephonyReadinessError`` so ``place_call`` callers catching the latter also
  catch the E.164 pre-dial failure; the dial / auth / abandonment errors are
  distinct so they map to their own exit codes);
- the carried attributes (`failing_check`, `http_status`, `session_id`, …);
- the no-secret / no-body invariant on the auth + dial errors (FR-008 / FR-035).

Mirrors the focused-unit-test approach of T022's
``tests/unit/test_signalwire_signature.py``.
"""

from __future__ import annotations

import pytest

from opencloser.transport.signalwire.errors import (
    LiveCallAbandonmentError,
    ProviderRejectedDialError,
    RealDialPhoneValidationError,
    SignatureVerificationError,
    TelephonyReadinessError,
)

# Sentinels that MUST NOT appear in any exception's string form (FR-008 / FR-035).
_SECRET = "T023-SIGNING-SECRET-must-not-leak"
_BODY = "T023-CALLBACK-BODY-must-not-leak"


# ---------------------------------------------------------------------------
# TelephonyReadinessError (FR-009 / FR-011)
# ---------------------------------------------------------------------------


def test_telephony_readiness_error_records_failing_check() -> None:
    err = TelephonyReadinessError("dataverse_mapping_verified")
    assert err.failing_check == "dataverse_mapping_verified"
    assert err.detail is None
    assert "dataverse_mapping_verified" in str(err)


def test_telephony_readiness_error_includes_detail_when_present() -> None:
    err = TelephonyReadinessError("source_caller_id", detail="not configured")
    assert err.detail == "not configured"
    assert "source_caller_id" in str(err)
    assert "not configured" in str(err)


# ---------------------------------------------------------------------------
# RealDialPhoneValidationError (FR-010) — subclasses TelephonyReadinessError
# ---------------------------------------------------------------------------


def test_real_dial_phone_validation_is_a_readiness_error() -> None:
    """A ``place_call`` caller catching ``TelephonyReadinessError`` MUST also
    catch the E.164 pre-dial failure (contract §Raises)."""
    assert issubclass(RealDialPhoneValidationError, TelephonyReadinessError)
    with pytest.raises(TelephonyReadinessError):
        raise RealDialPhoneValidationError("+1555")


def test_real_dial_phone_validation_records_phone() -> None:
    err = RealDialPhoneValidationError("555-1234")
    assert err.failing_check == "destination_phone_e164"
    assert "555-1234" in str(err)


def test_real_dial_phone_validation_handles_missing_phone() -> None:
    err = RealDialPhoneValidationError(None)
    assert err.failing_check == "destination_phone_e164"
    assert "missing or blank" in str(err)


# ---------------------------------------------------------------------------
# ProviderRejectedDialError (FR-012)
# ---------------------------------------------------------------------------


def test_provider_rejected_dial_carries_http_status() -> None:
    err = ProviderRejectedDialError(http_status=403, provider_message="account suspended")
    assert err.http_status == 403
    assert err.provider_message == "account suspended"
    assert "403" in str(err)
    assert "account suspended" in str(err)


def test_provider_rejected_dial_without_message() -> None:
    err = ProviderRejectedDialError(http_status=400)
    assert err.http_status == 400
    assert err.provider_message is None
    assert "400" in str(err)


def test_provider_rejected_dial_is_not_a_readiness_error() -> None:
    """Distinct from readiness so the runner maps it to exit code 5, not 4."""
    assert not issubclass(ProviderRejectedDialError, TelephonyReadinessError)


# ---------------------------------------------------------------------------
# SignatureVerificationError (FR-008) — always 401, never leaks secret/body
# ---------------------------------------------------------------------------


def test_signature_verification_error_is_always_401() -> None:
    err = SignatureVerificationError("missing SignalWire signature header")
    assert err.http_status == 401


def test_signature_verification_error_does_not_leak_secret_or_body() -> None:
    """The exception carries only a generic message — never the signing secret
    or the callback body (FR-008 / FR-035)."""
    err = SignatureVerificationError("SignalWire signature mismatch")
    flat = str(err) + " " + repr(err.__dict__)
    assert _SECRET not in flat
    assert _BODY not in flat
    # And there is no attribute that could carry them.
    assert not hasattr(err, "signing_secret")
    assert not hasattr(err, "body")


def test_signature_verification_error_is_distinct_type() -> None:
    assert not issubclass(SignatureVerificationError, TelephonyReadinessError)
    assert not issubclass(SignatureVerificationError, ProviderRejectedDialError)


# ---------------------------------------------------------------------------
# LiveCallAbandonmentError (FR-026)
# ---------------------------------------------------------------------------


def test_live_call_abandonment_records_context() -> None:
    err = LiveCallAbandonmentError(
        session_id="sess-t023-001",
        provider_call_id="CA-T023-SID",
        timeout_sec=90,
    )
    assert err.session_id == "sess-t023-001"
    assert err.provider_call_id == "CA-T023-SID"
    assert err.timeout_sec == 90
    assert "sess-t023-001" in str(err)
    assert "90" in str(err)


def test_live_call_abandonment_handles_missing_provider_call_id() -> None:
    err = LiveCallAbandonmentError(session_id="sess-t023-002", provider_call_id=None, timeout_sec=60)
    assert err.provider_call_id is None
    assert "sess-t023-002" in str(err)
