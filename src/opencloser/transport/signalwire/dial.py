"""SignalWire outbound dial (FR-004, FR-010, FR-012).

T024 (2026-05-31): real implementation. The ``SignalWireClient`` Protocol is the
narrow subset of the ``signalwire`` SDK this adapter consumes; it is
constructor-injected into ``SignalWireTransport`` (T026) so contract tests pass a
``FakeSignalWireClient`` without touching the real SDK or credentials
(``t013-clarify-questions.md`` Q4).

This module owns two responsibilities:

- :func:`build_swml_dial_plan` — construct the opaque SWML dial-plan string for a
  destination. SWML payload shapes MUST NOT leak past the ``transport/signalwire``
  boundary (contract §"What MUST NOT leak"); building it here keeps it inside.
- :func:`place_outbound_call` — validate the destination phone against E.164
  BEFORE any dial (raises ``RealDialPhoneValidationError`` per FR-010, never
  invoking ``create_call``), then place the call. A SignalWire 4xx surfaces as
  ``ProviderRejectedDialError`` (raised by the client) per FR-012.
"""

from __future__ import annotations

import json
import re
from typing import Protocol

from opencloser.models import DialPlan, ProviderCallId, QueueItem
from opencloser.transport.signalwire.errors import RealDialPhoneValidationError

# Anchored E.164: leading ``+``, a non-zero leading digit, then 1-14 more digits
# (2-15 digits total). Mirrors the Slice 2 runner's destination-phone gate; the
# transport owns its own pre-dial validation (FR-010) so it stays self-contained.
_E164_RE = re.compile(r"^\+[1-9]\d{1,14}$")


class SignalWireClient(Protocol):
    """The subset of the ``signalwire`` SDK surface this adapter consumes.

    Defined as a structural Protocol so contract tests can pass a
    ``FakeSignalWireClient`` (see ``tests/fixtures/signalwire/__init__.py``)
    without touching the real SDK.
    """

    def create_call(self, *, source: str, destination: str, dial_plan: DialPlan) -> str:
        """Place an outbound call. Returns the provider-assigned call SID.

        Raises ``ProviderRejectedDialError`` on any SignalWire 4xx response
        before placement.
        """
        ...


def is_e164(phone: str | None) -> bool:
    """Return ``True`` iff ``phone`` is a valid E.164 / provider-acceptable number."""
    return bool(phone) and bool(_E164_RE.match(phone))


def build_swml_dial_plan(
    *,
    destination: str,
    source_caller_id: str,
    status_callback_url: str | None = None,
) -> DialPlan:
    """Construct the SWML dial plan that connects an outbound call to ``destination``.

    Returns an opaque ``DialPlan`` (a serialized SWML document). Callers treat the
    result as opaque — the SWML shape MUST NOT be inspected or reconstructed
    outside the ``transport/signalwire`` boundary (contract §"What MUST NOT leak").
    """
    connect: dict[str, object] = {"to": destination, "from": source_caller_id}
    if status_callback_url is not None:
        connect["status_url"] = status_callback_url
    plan = {
        "version": "1.0.0",
        "sections": {"main": [{"connect": connect}]},
    }
    return json.dumps(plan, separators=(",", ":"), sort_keys=True)


def place_outbound_call(
    *,
    client: SignalWireClient,
    queue_item: QueueItem,
    dial_plan: DialPlan,
    source_caller_id: str,
) -> ProviderCallId:
    """Validate the destination phone (E.164 / provider-acceptable) and place
    a SignalWire outbound call. Returns the provider-assigned call SID.

    Raises:
        RealDialPhoneValidationError: pre-dial validation failure (FR-010). The
            destination is rejected BEFORE ``create_call`` is invoked, so no
            attempt is consumed and no Phone Call activity is created.
        ProviderRejectedDialError: SignalWire 4xx before placement (FR-012),
            raised by ``client.create_call``.
    """
    destination = queue_item.phone_number
    if not is_e164(destination):
        # Pre-dial gate: MUST raise before any provider interaction (FR-010).
        raise RealDialPhoneValidationError(destination)

    return client.create_call(
        source=source_caller_id,
        destination=destination,
        dial_plan=dial_plan,
    )
