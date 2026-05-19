"""Unit tests for MockWriteBackAdapter (FR-015 / FR-018 / FR-028-FR-031)."""

from __future__ import annotations

import sqlite3

import pytest

from opencloser.crm.mock import MockWriteBackAdapter
from opencloser.models import (
    CallableStatus,
    Disposition,
    PhoneCallActivityPayload,
    QueueItem,
    QueueStatusUpdatePayload,
    Session,
    SessionState,
    TaskPayload,
)
from opencloser.state import store

pytestmark = pytest.mark.module("crm")

_T = "2026-05-19T17:00:00.000Z"


def _seed_queue_item(conn: sqlite3.Connection) -> None:
    store.insert_queue_item(
        conn,
        QueueItem(
            queue_item_id="q1",
            facility_name="Sunset Ridge",
            phone_number="+15555550100",
            timezone="America/Los_Angeles",
            attempt_count=0,
            callable_status=CallableStatus.READY,
        ),
    )


def _seed_session(conn: sqlite3.Connection, *, disposition: Disposition | None = None) -> None:
    store.insert_session(
        conn,
        Session(
            session_id="ses_1",
            queue_item_id="q1",
            state=SessionState.FINALIZED if disposition else SessionState.IN_FLIGHT,
            final_disposition=disposition,
            started_at=_T,
            ended_at=_T if disposition else None,
        ),
    )


def _activity() -> PhoneCallActivityPayload:
    return PhoneCallActivityPayload(
        session_id="ses_1",
        queue_item_id="q1",
        mock_provider_call_id="call_x",
        persona_version="alf-appointment-setter@0.1.0",
        final_disposition=Disposition.INTERESTED_CALLBACK_REQUESTED,
        summary="Interested; callback Thursday 14:00.",
        started_at=_T,
        ended_at=_T,
    )


def _status(new_status: CallableStatus = CallableStatus.READY) -> QueueStatusUpdatePayload:
    return QueueStatusUpdatePayload(
        session_id="ses_1",
        queue_item_id="q1",
        previous_status=CallableStatus.READY,
        new_status=new_status,
        transition_reason="interested_callback_requested",
        transition_at=_T,
    )


def _callback_task() -> TaskPayload:
    return TaskPayload(
        task_id="task_1",
        session_id="ses_1",
        queue_item_id="q1",
        task_kind="callback",
        subject="Callback Thursday 14:00",
        preferred_callback_window="Thursday 14:00",
        captured_email="alice@example.com",
        persona_version="alf-appointment-setter@0.1.0",
        created_at=_T,
    )


# ---------------------------------------------------------------------------


def test_emit_all_three_payloads_round_trip(tmp_state_db: sqlite3.Connection) -> None:
    _seed_queue_item(tmp_state_db)
    _seed_session(tmp_state_db, disposition=Disposition.INTERESTED_CALLBACK_REQUESTED)
    adapter = MockWriteBackAdapter(tmp_state_db)

    adapter.emit_phone_call_activity(_activity())
    adapter.emit_queue_status_update(_status())
    adapter.emit_task(_callback_task())

    # Persisted rows exist.
    assert tmp_state_db.execute("SELECT COUNT(*) AS n FROM phone_call_activities;").fetchone()["n"] == 1
    assert tmp_state_db.execute("SELECT COUNT(*) AS n FROM queue_status_updates;").fetchone()["n"] == 1
    assert tmp_state_db.execute("SELECT COUNT(*) AS n FROM task_payloads;").fetchone()["n"] == 1

    # Aggregate is correct.
    wb = adapter.build_writeback("ses_1")
    assert wb.phone_call_activity is not None
    assert wb.queue_status_update is not None
    assert wb.task is not None
    assert wb.task.captured_email == "alice@example.com"


def test_build_writeback_raises_without_queue_status(tmp_state_db: sqlite3.Connection) -> None:
    _seed_queue_item(tmp_state_db)
    _seed_session(tmp_state_db)
    adapter = MockWriteBackAdapter(tmp_state_db)
    with pytest.raises(KeyError):
        adapter.build_writeback("ses_1")


def test_emit_task_belt_and_suspenders_blocks_excluded_dispositions(
    tmp_state_db: sqlite3.Connection,
) -> None:
    """FR-018: emit_task MUST silently no-op for not_interested / wrong_number /
    do_not_call / failed / blocked."""
    _seed_queue_item(tmp_state_db)
    for excluded in (
        Disposition.NOT_INTERESTED,
        Disposition.WRONG_NUMBER,
        Disposition.DO_NOT_CALL,
        Disposition.FAILED,
        Disposition.BLOCKED,
    ):
        # Reset the session's disposition for this iteration.
        tmp_state_db.execute("DELETE FROM sessions WHERE session_id = ?;", ("ses_1",))
        _seed_session(tmp_state_db, disposition=excluded)
        adapter = MockWriteBackAdapter(tmp_state_db)
        adapter.emit_task(_callback_task())
        # No row should be persisted.
        row = tmp_state_db.execute(
            "SELECT COUNT(*) AS n FROM task_payloads WHERE session_id = 'ses_1';"
        ).fetchone()
        assert row["n"] == 0, f"emit_task should no-op for disposition {excluded}"
        # Aggregate's task slot remains None.
        with pytest.raises(KeyError):
            adapter.build_writeback("ses_1")  # no queue_status yet either


def test_emit_task_permitted_for_needs_human_review(tmp_state_db: sqlite3.Connection) -> None:
    _seed_queue_item(tmp_state_db)
    _seed_session(tmp_state_db, disposition=Disposition.NEEDS_HUMAN_REVIEW)
    adapter = MockWriteBackAdapter(tmp_state_db)
    review_task = TaskPayload(
        task_id="task_2",
        session_id="ses_1",
        queue_item_id="q1",
        task_kind="review",
        subject="Review uncertain role",
        reason_code=__import__("opencloser.models", fromlist=["HumanReviewReason"]).HumanReviewReason.UNCERTAIN_ROLE,
        persona_version="alf-appointment-setter@0.1.0",
        created_at=_T,
    )
    adapter.emit_queue_status_update(_status(CallableStatus.BLOCKED))
    adapter.emit_task(review_task)
    row = tmp_state_db.execute(
        "SELECT task_kind, reason_code FROM task_payloads WHERE session_id = 'ses_1';"
    ).fetchone()
    assert row["task_kind"] == "review"
    assert row["reason_code"] == "uncertain_role"


def test_queue_status_payload_always_required(tmp_state_db: sqlite3.Connection) -> None:
    """FR-029: queue_status_update MUST be emitted exactly once per processed queue-item ID,
    including for blocked sessions."""
    _seed_queue_item(tmp_state_db)
    _seed_session(tmp_state_db, disposition=Disposition.BLOCKED)
    adapter = MockWriteBackAdapter(tmp_state_db)
    # Blocked session emits ONLY queue_status_update (no activity, no task).
    adapter.emit_queue_status_update(_status())
    wb = adapter.build_writeback("ses_1")
    assert wb.phone_call_activity is None
    assert wb.task is None
    assert wb.queue_status_update is not None
