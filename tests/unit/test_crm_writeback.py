"""Unit tests for MockWriteBackAdapter (FR-015 / FR-018 / FR-028-FR-031)."""

from __future__ import annotations

import sqlite3

import pytest

from opencloser.crm.base import WriteBackAdapter
from opencloser.crm.mock import MockWriteBackAdapter
from opencloser.models import (
    CallableStatus,
    Disposition,
    HumanReviewReason,
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
    assert (
        tmp_state_db.execute("SELECT COUNT(*) AS n FROM phone_call_activities;").fetchone()["n"]
        == 1
    )
    assert (
        tmp_state_db.execute("SELECT COUNT(*) AS n FROM queue_status_updates;").fetchone()["n"] == 1
    )
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
        reason_code=HumanReviewReason.UNCERTAIN_ROLE,
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


def test_emit_task_fail_closed_when_session_not_finalized(
    tmp_state_db: sqlite3.Connection,
) -> None:
    """L2 / FR-018: emit_task fails closed — it no-ops when the session has no final
    disposition yet, since FR-018 compliance cannot be verified without one."""
    _seed_queue_item(tmp_state_db)
    _seed_session(tmp_state_db)  # IN_FLIGHT, final_disposition is None
    adapter = MockWriteBackAdapter(tmp_state_db)
    adapter.emit_task(_callback_task())
    row = tmp_state_db.execute(
        "SELECT COUNT(*) AS n FROM task_payloads WHERE session_id = 'ses_1';"
    ).fetchone()
    assert row["n"] == 0


def test_emit_task_fail_closed_when_session_missing(
    tmp_state_db: sqlite3.Connection,
) -> None:
    """L2 / FR-018: emit_task no-ops when the referenced session does not exist."""
    _seed_queue_item(tmp_state_db)
    adapter = MockWriteBackAdapter(tmp_state_db)
    adapter.emit_task(_callback_task())  # ses_1 was never inserted
    row = tmp_state_db.execute(
        "SELECT COUNT(*) AS n FROM task_payloads WHERE session_id = 'ses_1';"
    ).fetchone()
    assert row["n"] == 0


def test_mock_adapter_satisfies_writeback_protocol(tmp_state_db: sqlite3.Connection) -> None:
    """M3 / FR-016: MockWriteBackAdapter structurally satisfies the runtime-checkable
    WriteBackAdapter Protocol — the Slice 1 runtime enforcement of the FR-033 boundary."""
    adapter = MockWriteBackAdapter(tmp_state_db)
    assert isinstance(adapter, WriteBackAdapter)


def test_task_payload_assigned_to_defaults_to_none() -> None:
    """Q19: assigned_to is OPTIONAL and the Slice 1 mock leaves it null. It is the
    explicit Slice 2 Dataverse wiring point (SC-008)."""
    task = _callback_task()
    assert task.assigned_to is None


def test_emit_queue_status_update_exactly_once_db_guard(
    tmp_state_db: sqlite3.Connection,
) -> None:
    """FR-029: queue_status_updates.session_id is a PRIMARY KEY — a second emit for the
    same session raises IntegrityError. This is the schema-level belt-and-suspenders
    behind the orchestrator's idempotency-key gate."""
    _seed_queue_item(tmp_state_db)
    _seed_session(tmp_state_db, disposition=Disposition.INTERESTED_CALLBACK_REQUESTED)
    adapter = MockWriteBackAdapter(tmp_state_db)
    adapter.emit_queue_status_update(_status())
    with pytest.raises(sqlite3.IntegrityError):
        adapter.emit_queue_status_update(_status())


def test_q5_verified_email_carried_into_callback_task(
    tmp_state_db: sqlite3.Connection,
) -> None:
    """Q5 carve-out: when a verified email accompanies a callback request, the captured
    email MUST be carried in the emitted callback task payload (FR-030 + FR-013)."""
    _seed_queue_item(tmp_state_db)
    _seed_session(tmp_state_db, disposition=Disposition.INTERESTED_CALLBACK_REQUESTED)
    adapter = MockWriteBackAdapter(tmp_state_db)
    adapter.emit_queue_status_update(_status())
    adapter.emit_task(_callback_task())

    # Persisted row carries both the callback window and the verified email.
    row = tmp_state_db.execute(
        "SELECT task_kind, preferred_callback_window, captured_email "
        "FROM task_payloads WHERE session_id = 'ses_1';"
    ).fetchone()
    assert row["task_kind"] == "callback"
    assert row["preferred_callback_window"] == "Thursday 14:00"
    assert row["captured_email"] == "alice@example.com"

    # And it surfaces on the composite WriteBack aggregate.
    wb = adapter.build_writeback("ses_1")
    assert wb.task is not None
    assert wb.task.captured_email == "alice@example.com"
    assert wb.task.preferred_callback_window == "Thursday 14:00"
