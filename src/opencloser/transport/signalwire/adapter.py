"""SignalWire transport adapter — the Slice 3 implementation of the Slice 1
call-transport conceptual contract (FR-004 – FR-008, FR-026).

Stub module — bodies land in T026. See
``contracts/signalwire-transport.md`` and ``specs/003-real-call-real-crm/
t013-clarify-questions.md`` (Q3: callbacks fed via ``ingest_callback``; Q4:
``SignalWireClient`` constructor-injected; Q5: stub-first TDD red).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from opencloser.models import CallEvent, DialPlan, ProviderCallId, QueueItem
from opencloser.transport.signalwire.dial import SignalWireClient


class SignalWireTransport:
    """Slice 1 ``CallTransport`` conceptual contract — SignalWire implementation.

    ``SignalWireClient`` is constructor-injected so contract tests can pass a
    ``FakeSignalWireClient`` without burning real credentials.
    """

    def __init__(
        self,
        *,
        client: SignalWireClient,
        source_caller_id: str,
        signing_secret: str,
    ) -> None:
        self._client = client
        self._source_caller_id = source_caller_id
        self._signing_secret = signing_secret

    async def place_call(
        self,
        queue_item: QueueItem,
        dial_plan: DialPlan,
        *,
        session_id: str,
    ) -> ProviderCallId:
        """Place an outbound SignalWire call. Returns the provider-assigned call SID.

        Raises:
            TelephonyReadinessError: pre-dial readiness check failed.
            RealDialPhoneValidationError: destination phone failed E.164 (FR-010).
            ProviderRejectedDialError: SignalWire 4xx before placement (FR-012).
        """

        raise NotImplementedError("T024 / T026 — place_call not yet implemented")  # pragma: no cover

    async def event_stream(self, provider_call_id: ProviderCallId) -> AsyncIterator[CallEvent]:
        """Yield normalized ``CallEvent`` instances as SignalWire callbacks arrive.

        Ends on the first normalized terminal event OR on live-call abandonment
        timeout per FR-026.
        """

        raise NotImplementedError("T025 / T026 — event_stream not yet implemented")  # pragma: no cover
        # Make this an async generator at type-check time even though we raise.
        yield  # type: ignore[unreachable]  # pragma: no cover

    async def ingest_callback(
        self,
        *,
        session_id: str,
        headers: dict[str, str],
        body: bytes,
    ) -> None:
        """Test / receiver entrypoint for an inbound SignalWire callback.

        Performs signature verification, dedup, ordering classification, audit
        log appends, and event enqueue. The HTTP-layer callback receiver (when
        bound in real-call mode) calls this same method.

        Raises ``SignatureVerificationError`` on any verification failure.
        """

        raise NotImplementedError("T022 / T025 — ingest_callback not yet implemented")  # pragma: no cover
