"""Test fakes for the SignalWire SDK surface (Q4 of T013 clarify questions).

``FakeSignalWireClient`` implements the ``SignalWireClient`` Protocol from
``opencloser.transport.signalwire.dial`` so contract tests can exercise the
adapter without burning real credentials and without monkey-patching the
SDK. Tests construct one with a queued response sequence:

    client = FakeSignalWireClient(responses=[CallCreated(sid="CA-1")])
    transport = SignalWireTransport(client=client, source_caller_id=...,
                                     signing_secret=...)
    await transport.place_call(...)
    assert client.calls_placed == 1
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from opencloser.transport.signalwire.errors import ProviderRejectedDialError


@dataclass(frozen=True)
class CallCreated:
    """Successful ``create_call`` response."""

    sid: str


@dataclass(frozen=True)
class CallRejected:
    """4xx ``create_call`` response (FR-012). The fake raises
    ``ProviderRejectedDialError(http_status, provider_message)`` when this
    response is dequeued."""

    http_status: int = 400
    provider_message: str | None = None


@dataclass
class _PlacedCall:
    source: str
    destination: str
    dial_plan: str


@dataclass
class FakeSignalWireClient:
    """In-memory fake implementing the ``SignalWireClient`` Protocol.

    Responses are dequeued in order. An empty queue yields a default
    ``CallCreated(sid="CA-FAKE")``.
    """

    responses: deque[CallCreated | CallRejected] = field(default_factory=deque)
    placed_calls: list[_PlacedCall] = field(default_factory=list)

    @property
    def calls_placed(self) -> int:
        return len(self.placed_calls)

    def queue_response(self, response: CallCreated | CallRejected) -> None:
        self.responses.append(response)

    def create_call(self, *, source: str, destination: str, dial_plan: str) -> str:
        response = self.responses.popleft() if self.responses else CallCreated(sid="CA-FAKE")
        if isinstance(response, CallRejected):
            # Per FR-012 we DO NOT record the placed call when the provider
            # rejects it pre-placement.
            raise ProviderRejectedDialError(
                http_status=response.http_status,
                provider_message=response.provider_message,
            )
        self.placed_calls.append(_PlacedCall(source=source, destination=destination, dial_plan=dial_plan))
        return response.sid
