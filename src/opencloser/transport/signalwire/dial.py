"""SignalWire outbound dial (FR-004, FR-010, FR-012).

Stub module — bodies land in T024. See
``contracts/signalwire-transport.md`` and ``specs/003-real-call-real-crm/
t013-clarify-questions.md`` (Q4: SignalWireClient is constructor-injected
into ``SignalWireTransport``; this module's helper takes the client as a
parameter rather than constructing it).
"""

from __future__ import annotations

from typing import Protocol

from opencloser.models import DialPlan, ProviderCallId, QueueItem


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
        RealDialPhoneValidationError: pre-dial validation failure (FR-010).
        ProviderRejectedDialError: SignalWire 4xx before placement (FR-012).
    """

    raise NotImplementedError("T024 — outbound dial not yet implemented")  # pragma: no cover
