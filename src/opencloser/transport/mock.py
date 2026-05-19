"""FixtureDrivenTransport — Slice 1 mock implementation of FR-008's CallTransport contract.

Reads a transport fixture JSON file at place_call time; yields its events verbatim via
event_stream. Stateless with respect to opencloser persistence — the orchestrator records
events as they arrive.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from opencloser.core import ids
from opencloser.models import EventType, MockCallEvent, QueueItem


class FixtureDrivenTransport:
    """Stateless transport that yields a fixture's events in order."""

    def __init__(self, fixtures_dir: str | Path) -> None:
        self._fixtures_dir = Path(fixtures_dir)
        # Map mock_provider_call_id → fixture path so event_stream can replay.
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
        """FR-006: yield events from the fixture in order. Duplicates are yielded verbatim
        (FR-019 dedup is the orchestrator's job)."""
        fixture_path = self._pending.pop(mock_provider_call_id, None)
        if fixture_path is None:
            raise ValueError(f"No fixture pending for {mock_provider_call_id!r}")
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        for raw_event in data.get("events", []):
            event_type_str = raw_event["type"]
            try:
                event_type = EventType(event_type_str)
            except ValueError:
                # Per Clarifications: unknown event types are yielded verbatim;
                # orchestrator decides what to do with them (log, no-op).
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
