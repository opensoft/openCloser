"""FixtureDrivenTransport — Slice 1 mock implementation of FR-008's CallTransport contract.

Reads a transport fixture JSON file at place_call time; yields its events verbatim via
event_stream. Stateless with respect to opencloser persistence — the orchestrator records
events as they arrive.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path

from opencloser.core import ids
from opencloser.models import EventType, MockCallEvent, QueueItem

logger = logging.getLogger(__name__)


class FixtureDrivenTransport:
    """Stateless transport that yields a fixture's events in order."""

    def __init__(self, fixtures_dir: str | Path) -> None:
        self._fixtures_dir = Path(fixtures_dir)
        # Map mock_provider_call_id → fixture path; consumed (one-shot) by event_stream.
        self._pending: dict[str, Path] = {}

    def place_call(self, queue_item: QueueItem, fixture_id: str) -> str:
        """FR-007: assign a globally-unique mock_provider_call_id and stash the fixture path."""
        del queue_item  # unused; the fixture itself carries the queue_item_ref
        fixture_path = self._resolve_fixture_path(fixture_id)
        if not fixture_path.exists():
            raise FileNotFoundError(f"Transport fixture not found: {fixture_path}")
        call_id = ids.new_mock_provider_call_id()
        self._pending[call_id] = fixture_path
        return call_id

    def event_stream(self, mock_provider_call_id: str) -> Iterator[MockCallEvent]:
        """FR-006: yield the fixture's events in order for a placed call.

        One-shot per call id: the pending fixture mapping is consumed on the first
        call, so each ``mock_provider_call_id`` may be streamed exactly once. A
        second call with the same id (or an id that was never placed) raises
        ``ValueError``. Callers that need the events again must persist them — the
        orchestrator does, on insert.

        Duplicate events are yielded verbatim; FR-019 deduplication is the
        orchestrator's job, not the transport's.

        ``session_id`` caveat: the transport operates at the call layer and has no
        session_id. The yielded ``MockCallEvent.session_id`` field therefore
        carries the ``mock_provider_call_id`` as a stand-in value; the orchestrator
        rewrites it to the real session_id when it persists the event (see
        ``core/orchestrator.py``). Both fields are plain ``str``, so this
        substitution is not type-checked — splitting a session-less
        ``TransportEvent`` type out of ``MockCallEvent`` is a Slice 2 cleanup
        (see contracts/transport.md).
        """
        fixture_path = self._pending.pop(mock_provider_call_id, None)
        if fixture_path is None:
            raise ValueError(f"No fixture pending for {mock_provider_call_id!r}")
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        for raw_event in data.get("events", []):
            event_type_str = raw_event["type"]
            try:
                event_type = EventType(event_type_str)
            except ValueError:
                # Edge Case "Mock transport emits an unknown event type": the system
                # MUST log it, MUST NOT mutate state, MUST NOT crash. The transport
                # skips the event (the orchestrator never sees it), so the transport
                # itself is responsible for the log.
                logger.warning(
                    "transport fixture %s: unknown event type %r (event_id=%s) — skipping",
                    fixture_path.name,
                    event_type_str,
                    raw_event.get("event_id"),
                )
                continue
            yield MockCallEvent(
                session_id=mock_provider_call_id,  # orchestrator rewrites to session_id on insert
                event_id=raw_event["event_id"],
                event_type=event_type,
                received_at=raw_event["timestamp"],
                payload=raw_event.get("payload", {}),
            )

    def _resolve_fixture_path(self, fixture_id: str) -> Path:
        # Accept either a bare fixture_id ("no_answer") or a full filename ("no_answer.json").
        if fixture_id.endswith(".json"):
            return self._fixtures_dir / fixture_id
        return self._fixtures_dir / f"{fixture_id}.json"
