"""Unit tests for idempotency-key helpers (FR-019 + research.md §Cross-cutting)."""

from __future__ import annotations

import sqlite3

import pytest

from opencloser.core import idempotency
from opencloser.models import (
    CallableStatus,
    QueueItem,
    Session,
    SessionState,
    WriteBackKind,
)
from opencloser.state import store

pytestmark = pytest.mark.module("core")

_T = "2026-05-19T17:00:00.000Z"


def _seed(conn: sqlite3.Connection) -> None:
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
    store.insert_session(
        conn,
        Session(
            session_id="ses_1",
            queue_item_id="q1",
            state=SessionState.CREATED,
            started_at=_T,
        ),
    )


def test_compute_key_deterministic() -> None:
    a = idempotency.compute_key(
        session_id="ses_1",
        mock_provider_call_id="call_x",
        event_id="evt_1",
        write_back_kind=WriteBackKind.PHONE_CALL_ACTIVITY,
    )
    b = idempotency.compute_key(
        session_id="ses_1",
        mock_provider_call_id="call_x",
        event_id="evt_1",
        write_back_kind=WriteBackKind.PHONE_CALL_ACTIVITY,
    )
    assert a == b
    assert a.as_tuple() == ("ses_1", "call_x", "evt_1", "phone_call_activity")


def test_record_or_skip_first_insert_succeeds(tmp_state_db: sqlite3.Connection) -> None:
    _seed(tmp_state_db)
    key = idempotency.compute_key(
        session_id="ses_1",
        mock_provider_call_id="call_x",
        event_id="evt_1",
        write_back_kind=WriteBackKind.SESSION_STATE,
    )
    assert idempotency.record_or_skip(tmp_state_db, key, applied_at=_T) is True


def test_record_or_skip_duplicate_returns_false(tmp_state_db: sqlite3.Connection) -> None:
    _seed(tmp_state_db)
    key = idempotency.compute_key(
        session_id="ses_1",
        mock_provider_call_id="call_x",
        event_id="evt_1",
        write_back_kind=WriteBackKind.NORMALIZED_RESULT,
    )
    assert idempotency.record_or_skip(tmp_state_db, key, applied_at=_T) is True
    assert idempotency.record_or_skip(tmp_state_db, key, applied_at=_T) is False


def test_record_or_skip_different_write_back_kinds(tmp_state_db: sqlite3.Connection) -> None:
    _seed(tmp_state_db)
    for kind in (
        WriteBackKind.SESSION_STATE,
        WriteBackKind.ATTEMPT_COUNT,
        WriteBackKind.PHONE_CALL_ACTIVITY,
        WriteBackKind.QUEUE_STATUS_UPDATE,
        WriteBackKind.TASK_PAYLOAD,
        WriteBackKind.EXPORTED_ARTIFACT,
    ):
        key = idempotency.compute_key(
            session_id="ses_1",
            mock_provider_call_id="call_x",
            event_id="evt_1",
            write_back_kind=kind,
        )
        assert idempotency.record_or_skip(tmp_state_db, key, applied_at=_T) is True


def test_record_or_skip_null_event_id(tmp_state_db: sqlite3.Connection) -> None:
    """attempt_count increments key on (session, mock_provider_call_id, None, attempt_count)."""
    _seed(tmp_state_db)
    key = idempotency.compute_key(
        session_id="ses_1",
        mock_provider_call_id="call_x",
        event_id=None,
        write_back_kind=WriteBackKind.ATTEMPT_COUNT,
    )
    assert idempotency.record_or_skip(tmp_state_db, key, applied_at=_T) is True
    assert idempotency.record_or_skip(tmp_state_db, key, applied_at=_T) is False
