"""Unit tests for the SQLite state-store DAO (FR-022 + data-model.md)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from opencloser.models import (
    CallableStatus,
    ConflictingEventAuditRecord,
    Disposition,
    EligibilityDecision,
    EventType,
    MockCallEvent,
    QueueItem,
    Session,
    SessionState,
)
from opencloser.state import store

pytestmark = pytest.mark.module("state")

_T = "2026-05-19T17:00:00.000Z"


def _make_queue_item(qid: str = "q1") -> QueueItem:
    return QueueItem(
        queue_item_id=qid,
        facility_name="Sunset Ridge",
        phone_number="+15555550100",
        timezone="America/Los_Angeles",
        attempt_count=0,
        callable_status=CallableStatus.READY,
    )


def _make_session(sid: str = "ses_1", qid: str = "q1", **overrides: object) -> Session:
    base = {
        "session_id": sid,
        "queue_item_id": qid,
        "state": SessionState.CREATED,
        "started_at": _T,
    }
    base.update(overrides)
    return Session(**base)


# -- connection management ---------------------------------------------------


def test_connect_with_bare_filename_does_not_chmod_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bare DB filename has parent ".", and `connect()` must NOT chmod the CWD —
    doing so would change permissions for the whole checkout."""
    monkeypatch.chdir(tmp_path)
    tmp_path.chmod(0o755)
    conn = store.connect("bare.db")
    try:
        assert (tmp_path / "bare.db").exists()
        assert tmp_path.stat().st_mode & 0o777 == 0o755  # CWD mode left untouched
    finally:
        conn.close()


def test_connect_hardens_created_state_dir_only(tmp_path: Path) -> None:
    """connect() hardens a state directory it creates (0o700) but leaves a
    pre-existing directory's permissions untouched."""
    existing = tmp_path / "existing"
    existing.mkdir()
    existing.chmod(0o755)
    store.connect(existing / "a.db").close()
    assert existing.stat().st_mode & 0o777 == 0o755  # pre-existing dir untouched

    created = tmp_path / "fresh" / "nested"
    store.connect(created / "b.db").close()
    assert created.stat().st_mode & 0o777 == 0o700  # dir created by connect() hardened


# -- idempotency keys --------------------------------------------------------


def test_try_record_idempotency_key_reraises_non_duplicate_integrity_error(
    tmp_state_db: sqlite3.Connection,
) -> None:
    """A non-duplicate integrity failure (here a foreign-key violation — no such
    session) must surface, not be silently swallowed as a duplicate no-op."""
    with pytest.raises(sqlite3.IntegrityError):
        store.try_record_idempotency_key(
            tmp_state_db,
            session_id="ghost-session",
            mock_provider_call_id="",
            event_id="",
            write_back_kind="session_state",
            applied_at=_T,
        )


# -- schema bootstrapping ----------------------------------------------------


def test_init_schema_creates_tables(tmp_state_db: sqlite3.Connection) -> None:
    rows = tmp_state_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
    ).fetchall()
    names = {r["name"] for r in rows}
    for expected in {
        "queue_items",
        "sessions",
        "eligibility_decisions",
        "mock_call_events",
        "idempotency_keys",
        "conflicting_event_audit_records",
        "phone_call_activities",
        "queue_status_updates",
        "task_payloads",
        "normalized_results",
        "schema_meta",
    }:
        assert expected in names


def test_init_schema_seeds_schema_meta_once(tmp_state_db: sqlite3.Connection) -> None:
    count = tmp_state_db.execute("SELECT COUNT(*) AS n FROM schema_meta;").fetchone()["n"]
    assert count == 1
    store.init_schema(tmp_state_db, now_utc_ms=_T)
    count = tmp_state_db.execute("SELECT COUNT(*) AS n FROM schema_meta;").fetchone()["n"]
    assert count == 1, "init_schema must be idempotent"


# -- queue_items -------------------------------------------------------------


def test_queue_item_round_trip(tmp_state_db: sqlite3.Connection) -> None:
    item = _make_queue_item()
    store.insert_queue_item(tmp_state_db, item)
    restored = store.get_queue_item(tmp_state_db, item.queue_item_id)
    assert restored == item


def test_increment_attempt_count(tmp_state_db: sqlite3.Connection) -> None:
    store.insert_queue_item(tmp_state_db, _make_queue_item())
    store.increment_attempt_count(tmp_state_db, "q1")
    store.increment_attempt_count(tmp_state_db, "q1")
    restored = store.get_queue_item(tmp_state_db, "q1")
    assert restored is not None
    assert restored.attempt_count == 2


def test_update_queue_item_status_partial(tmp_state_db: sqlite3.Connection) -> None:
    store.insert_queue_item(tmp_state_db, _make_queue_item())
    store.update_queue_item_status(
        tmp_state_db,
        "q1",
        callable_status=CallableStatus.DNC,
        dnc_flag=True,
        last_decision_at=_T,
    )
    restored = store.get_queue_item(tmp_state_db, "q1")
    assert restored is not None
    assert restored.callable_status is CallableStatus.DNC
    assert restored.dnc_flag is True
    assert restored.last_decision_at == _T


def test_replace_queue_item_mutable_fields_overwrites_all_columns(
    tmp_state_db: sqlite3.Connection,
) -> None:
    """`replace_queue_item_mutable_fields` mirrors a fresh source snapshot
    onto local state — every mutable column moves to the snapshot value."""
    store.insert_queue_item(tmp_state_db, _make_queue_item())
    snapshot = QueueItem(
        queue_item_id="q1",
        facility_name="Renamed Facility",
        phone_number="+19998887777",
        timezone="America/New_York",
        default_tz_applied=True,
        email="ops@example.com",
        attempt_count=3,
        dnc_flag=True,
        callable_status=CallableStatus.BLOCKED,
        last_decision_at=_T,
    )
    store.replace_queue_item_mutable_fields(tmp_state_db, snapshot)
    restored = store.get_queue_item(tmp_state_db, "q1")
    assert restored == snapshot


def test_replace_queue_item_mutable_fields_clears_nullable_columns(
    tmp_state_db: sqlite3.Connection,
) -> None:
    """The replace DAO must propagate null clears — Dataverse can legitimately
    blank out phone/timezone/email, and stale local values would corrupt
    eligibility decisions on the next run."""
    store.insert_queue_item(tmp_state_db, _make_queue_item())
    # Verify the seed had non-null values.
    seeded = store.get_queue_item(tmp_state_db, "q1")
    assert seeded is not None
    assert seeded.phone_number is not None and seeded.timezone is not None

    cleared = QueueItem(
        queue_item_id="q1",
        facility_name="Sunset Ridge",
        phone_number=None,
        timezone=None,
        email=None,
        attempt_count=0,
        callable_status=CallableStatus.READY,
    )
    store.replace_queue_item_mutable_fields(tmp_state_db, cleared)
    restored = store.get_queue_item(tmp_state_db, "q1")
    assert restored is not None
    assert restored.phone_number is None
    assert restored.timezone is None
    assert restored.email is None


def test_replace_queue_item_mutable_fields_preserves_fk_children(
    tmp_state_db: sqlite3.Connection,
) -> None:
    """Refreshing the queue row must not cascade-delete dependent sessions —
    only the mutable columns change; the FK remains intact."""
    store.insert_queue_item(tmp_state_db, _make_queue_item())
    store.insert_session(tmp_state_db, _make_session())
    store.replace_queue_item_mutable_fields(
        tmp_state_db,
        QueueItem(
            queue_item_id="q1",
            facility_name="Refreshed",
            phone_number=None,
            timezone=None,
            attempt_count=7,
            dnc_flag=True,
            callable_status=CallableStatus.DNC,
        ),
    )
    # The session row still exists and still resolves its FK.
    restored = store.get_session(tmp_state_db, "ses_1")
    assert restored is not None
    assert restored.queue_item_id == "q1"
    rows = tmp_state_db.execute(
        "SELECT COUNT(*) AS n FROM sessions WHERE queue_item_id = 'q1';"
    ).fetchone()
    assert rows["n"] == 1


# -- sessions ----------------------------------------------------------------


def test_session_round_trip(tmp_state_db: sqlite3.Connection) -> None:
    store.insert_queue_item(tmp_state_db, _make_queue_item())
    sess = _make_session()
    store.insert_session(tmp_state_db, sess)
    restored = store.get_session(tmp_state_db, "ses_1")
    assert restored == sess


def test_session_blocked_terminal(tmp_state_db: sqlite3.Connection) -> None:
    store.insert_queue_item(tmp_state_db, _make_queue_item())
    sess = _make_session(
        state=SessionState.BLOCKED,
        final_disposition=Disposition.BLOCKED,
        blocked_reason=["d"],
        ended_at=_T,
    )
    store.insert_session(tmp_state_db, sess)
    restored = store.get_session(tmp_state_db, "ses_1")
    assert restored is not None
    assert restored.blocked_reason == ["d"]
    assert restored.final_disposition is Disposition.BLOCKED


def test_session_mock_provider_call_id_unique(tmp_state_db: sqlite3.Connection) -> None:
    store.insert_queue_item(tmp_state_db, _make_queue_item())
    store.insert_session(
        tmp_state_db,
        _make_session(sid="ses_1", mock_provider_call_id="call_x"),
    )
    with pytest.raises(sqlite3.IntegrityError):
        store.insert_session(
            tmp_state_db,
            _make_session(sid="ses_2", mock_provider_call_id="call_x"),
        )


# -- eligibility_decisions ---------------------------------------------------


def test_eligibility_decision_insert(tmp_state_db: sqlite3.Connection) -> None:
    store.insert_queue_item(tmp_state_db, _make_queue_item())
    store.insert_session(tmp_state_db, _make_session())
    decision = EligibilityDecision(
        decision_id="dec_1",
        queue_item_id="q1",
        decided_at=_T,
        outcome="block",
        rule_a_phone_pass=True,
        rule_b_timezone_pass=True,
        rule_c_call_window_pass=True,
        rule_d_dnc_pass=False,
        rule_e_max_attempts_pass=True,
        rule_f_callable_status_pass=True,
        failing_rules=["d"],
        session_id="ses_1",
    )
    store.insert_eligibility_decision(tmp_state_db, decision)
    row = tmp_state_db.execute(
        "SELECT outcome, failing_rules FROM eligibility_decisions WHERE decision_id = ?;",
        ("dec_1",),
    ).fetchone()
    assert row["outcome"] == "block"
    assert row["failing_rules"] == '["d"]'


# -- mock_call_events --------------------------------------------------------


def test_mock_call_event_round_trip(tmp_state_db: sqlite3.Connection) -> None:
    store.insert_queue_item(tmp_state_db, _make_queue_item())
    store.insert_session(tmp_state_db, _make_session())
    event = MockCallEvent(
        session_id="ses_1",
        event_id="evt_1",
        event_type=EventType.CONNECTED,
        received_at=_T,
    )
    store.insert_mock_call_event(tmp_state_db, event)
    events = store.list_mock_call_events(tmp_state_db, "ses_1")
    assert events == [event]


def test_mock_call_event_duplicate_pk_raises(tmp_state_db: sqlite3.Connection) -> None:
    store.insert_queue_item(tmp_state_db, _make_queue_item())
    store.insert_session(tmp_state_db, _make_session())
    event = MockCallEvent(
        session_id="ses_1", event_id="evt_1", event_type=EventType.CONNECTED, received_at=_T
    )
    store.insert_mock_call_event(tmp_state_db, event)
    with pytest.raises(sqlite3.IntegrityError):
        store.insert_mock_call_event(tmp_state_db, event)


# -- FK cascade --------------------------------------------------------------


def test_queue_item_delete_cascades_session(tmp_state_db: sqlite3.Connection) -> None:
    store.insert_queue_item(tmp_state_db, _make_queue_item())
    store.insert_session(tmp_state_db, _make_session())
    tmp_state_db.execute("DELETE FROM queue_items WHERE queue_item_id = ?;", ("q1",))
    assert store.get_session(tmp_state_db, "ses_1") is None


# -- conflicting events ------------------------------------------------------


def test_conflicting_event_round_trip(tmp_state_db: sqlite3.Connection) -> None:
    store.insert_queue_item(tmp_state_db, _make_queue_item())
    store.insert_session(tmp_state_db, _make_session())
    audit = ConflictingEventAuditRecord(
        audit_id="audit_1",
        session_id="ses_1",
        event_id="evt_late",
        conflicting_event_type=EventType.FAILED,
        received_at=_T,
        full_event_payload={"failure_reason": "carrier_error"},
        preserved_disposition=Disposition.NO_ANSWER,
    )
    store.insert_conflicting_event(tmp_state_db, audit)
    rows = store.list_conflicting_events(tmp_state_db, "ses_1")
    assert rows == [audit]
