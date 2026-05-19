"""MockWriteBackAdapter — Slice 1 implementation of FR-016 WriteBackAdapter contract.

Owns payload PERSISTENCE only. The orchestrator decides WHICH payloads to emit (per
FR-031); this adapter executes those decisions. Belt-and-suspenders enforcement of
FR-018's task exclusion is included so a stray `emit_task` call for a disposition in
the exclusion set is silently dropped.
"""

from __future__ import annotations

import sqlite3

from opencloser.models import (
    Disposition,
    PhoneCallActivityPayload,
    QueueStatusUpdatePayload,
    TaskPayload,
    WriteBack,
)
from opencloser.state import store

# FR-018 + Phase-1 decision: these dispositions MUST NOT emit any task payload.
_TASK_EXCLUDED_DISPOSITIONS: frozenset[Disposition] = frozenset(
    {
        Disposition.NOT_INTERESTED,
        Disposition.WRONG_NUMBER,
        Disposition.DO_NOT_CALL,
        Disposition.FAILED,
        Disposition.BLOCKED,
    }
)


class MockWriteBackAdapter:
    """Persists CRM write-back payloads to SQLite and tracks an in-memory aggregate per session."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        # session_id → composite WriteBack aggregate (kept in-memory so the orchestrator can export it)
        self._aggregates: dict[str, _AggregateBuilder] = {}

    # ----- emit_* methods ---------------------------------------------------

    def emit_phone_call_activity(self, payload: PhoneCallActivityPayload) -> None:
        store.insert_phone_call_activity(self._conn, payload)
        self._aggregate(payload.session_id).phone_call_activity = payload

    def emit_queue_status_update(self, payload: QueueStatusUpdatePayload) -> None:
        store.insert_queue_status_update(self._conn, payload)
        self._aggregate(payload.session_id).queue_status_update = payload

    def emit_task(self, payload: TaskPayload) -> None:
        # Belt-and-suspenders enforcement of FR-018 — even if the orchestrator misroutes,
        # the adapter refuses to persist a task for an excluded disposition.
        session = store.get_session(self._conn, payload.session_id)
        if session is not None and session.final_disposition in _TASK_EXCLUDED_DISPOSITIONS:
            return  # silent no-op per FR-018
        store.insert_task_payload(self._conn, payload)
        self._aggregate(payload.session_id).task = payload

    # ----- aggregate access -------------------------------------------------

    def build_writeback(self, session_id: str) -> WriteBack:
        """Return the composite WriteBack artifact for the given session.

        Raises KeyError if no queue-status update has been emitted yet (which is required
        for every session per FR-029)."""
        agg = self._aggregates.get(session_id)
        if agg is None or agg.queue_status_update is None:
            raise KeyError(f"No queue-status update emitted for session {session_id!r} yet")
        return WriteBack(
            session_id=session_id,
            phone_call_activity=agg.phone_call_activity,
            queue_status_update=agg.queue_status_update,
            task=agg.task,
        )

    # ----- internal ---------------------------------------------------------

    def _aggregate(self, session_id: str) -> _AggregateBuilder:
        agg = self._aggregates.get(session_id)
        if agg is None:
            agg = _AggregateBuilder()
            self._aggregates[session_id] = agg
        return agg


class _AggregateBuilder:
    """Mutable holder for one session's in-progress WriteBack."""

    __slots__ = ("phone_call_activity", "queue_status_update", "task")

    def __init__(self) -> None:
        self.phone_call_activity: PhoneCallActivityPayload | None = None
        self.queue_status_update: QueueStatusUpdatePayload | None = None
        self.task: TaskPayload | None = None
