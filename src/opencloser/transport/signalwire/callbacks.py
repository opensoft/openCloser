"""SignalWire status + media callback normalization (FR-005, FR-007, FR-021, FR-027).

Stub module — bodies land in T025. See
``contracts/signalwire-transport.md`` and ``specs/003-real-call-real-crm/
t013-clarify-questions.md`` (Q1: dedup flags carried on ``CallEvent``; Q2:
dedup state mirrored to SQLite ``signalwire_callbacks`` table for audit).
"""

from __future__ import annotations

from opencloser.models import CallEvent


def normalize_callback(*, session_id: str, headers: dict[str, str], body: bytes) -> CallEvent:
    """Translate a SignalWire callback payload into a normalized ``CallEvent``.

    The returned event carries the three Slice 3 delivery-state flags
    (``is_duplicate``, ``out_of_order``, ``late_after_finalization``)
    populated per the dedup ledger. Provider intermediate state names
    (``ringing`` / ``in_progress`` / ``busy`` / ``canceled``) MUST be mapped
    to the six normalized ``event_type`` values and MUST NOT leak into the
    returned event's fields.
    """

    raise NotImplementedError("T025 — callback normalization not yet implemented")  # pragma: no cover
