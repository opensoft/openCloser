"""Mock Call Transport ABC — FR-033 module boundary #3.

Contract: see specs/001-mock-call-mock-crm/contracts/transport.md
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol, runtime_checkable

from opencloser.models import MockCallEvent, QueueItem


@runtime_checkable
class CallTransport(Protocol):
    """FR-008 conceptual contract — the only path through which call-level events enter the Core."""

    def pre_validate_fixture(self, fixture_id: str) -> None:  # pragma: no cover - protocol
        """FR-019/FR-020 (Slice 2 addendum): side-effect-free structural pre-validation
        of the selected transport fixture. MUST be safe to call before any DB write so
        the orchestrator can gate session/decision/attempt persistence on it without
        placing a (future-real) call attempt. Raises ``MalformedFixtureError``
        (a ``ValueError`` subclass) on any structural failure.
        """
        ...

    def place_call(
        self, queue_item: QueueItem, fixture_id: str
    ) -> str:  # pragma: no cover - protocol
        """Initiate a call attempt. Return a globally-unique `mock_provider_call_id` (FR-007)."""
        ...

    def event_stream(
        self, mock_provider_call_id: str
    ) -> Iterator[MockCallEvent]:  # pragma: no cover - protocol
        """Yield events for the given mock_provider_call_id in fixture order (FR-006)."""
        ...
