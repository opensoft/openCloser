"""Slice 3 SignalWire transport exception hierarchy.

The five exception types raised by the SignalWire transport adapter. Each
maps to a distinct pre-dial or post-dial failure mode named in spec FR-008,
FR-010, FR-012, FR-013, and FR-026.

T023 (2026-05-31): real hierarchy. ``RealDialPhoneValidationError`` subclasses
``TelephonyReadinessError`` so a ``place_call`` caller catching the latter also
catches the E.164 pre-dial failure (contract: ``signalwire-transport.md`` §Raises).
``SignatureVerificationError`` and ``ProviderRejectedDialError`` carry an
``http_status`` for the embedded callback receiver, and — per FR-008 / FR-035 —
their messages MUST NOT include the signing secret or the callback body. See
``contracts/signalwire-transport.md`` and ``tests/unit/test_signalwire_errors.py``.
"""

from __future__ import annotations


class TelephonyReadinessError(Exception):
    """Raised when a pre-dial telephony readiness check fails (FR-009 / FR-011).

    The transport MUST NOT consume an attempt, MUST NOT place a SignalWire
    call, and MUST NOT create a Phone Call activity when this is raised.
    """

    def __init__(self, failing_check: str, detail: str | None = None) -> None:
        self.failing_check = failing_check
        self.detail = detail
        super().__init__(f"telephony readiness failed: {failing_check}" + (f" — {detail}" if detail else ""))


class RealDialPhoneValidationError(TelephonyReadinessError):
    """Raised when the destination phone fails E.164 / provider validation (FR-010)."""

    def __init__(self, destination_phone: str | None) -> None:
        super().__init__(
            failing_check="destination_phone_e164",
            detail=f"phone={destination_phone!r}" if destination_phone else "missing or blank",
        )


class ProviderRejectedDialError(Exception):
    """Raised when SignalWire returns 4xx before call placement (FR-012).

    The transport MUST NOT consume an attempt, MUST NOT create a Phone Call
    activity. The orchestrator advances the Dataverse queue per the existing
    per-disposition mapping for blocked / failed cases.
    """

    http_status: int

    def __init__(self, http_status: int, provider_message: str | None = None) -> None:
        self.http_status = http_status
        self.provider_message = provider_message
        super().__init__(f"provider rejected dial: HTTP {http_status}" + (f" — {provider_message}" if provider_message else ""))


class SignatureVerificationError(Exception):
    """Raised when an inbound SignalWire callback fails HMAC-SHA256 verification (FR-008).

    Carries the response HTTP status (always 401 per FR-008) so the embedded
    callback receiver can return the correct status without re-translating.
    MUST NOT carry the signing secret, MUST NOT carry the callback body.
    """

    http_status: int = 401


class LiveCallAbandonmentError(Exception):
    """Raised when a placed call does not reach a normalized terminal event
    within the configured live-call abandonment timeout (FR-026)."""

    def __init__(self, session_id: str, provider_call_id: str | None, timeout_sec: int) -> None:
        self.session_id = session_id
        self.provider_call_id = provider_call_id
        self.timeout_sec = timeout_sec
        super().__init__(
            f"live-call abandonment: session={session_id} provider_call_id={provider_call_id} "
            f"after {timeout_sec}s"
        )
