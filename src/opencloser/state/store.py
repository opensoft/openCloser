"""SQLite state store and DAO for Slice 1 (data-model.md, research.md §State store).

Stateless module: each public function takes an explicit ``sqlite3.Connection`` or a
context manager that yields one. The orchestrator owns connection lifetime.

**Slice 2 retention contract (FR-023, T041)**:

- The Slice 2 ``crm_correlations`` and ``writeback_progress`` rows are retained for
  **at least 90 days**, or until local audit-artifact retention (FR-035) expires —
  whichever is longer — so a later CLI re-invocation can resume a partial write-back
  within the documented window (FR-023, SC-014).
- The application **MUST NOT auto-delete** any of those rows. There are no DELETE
  statements against ``crm_correlations`` or ``writeback_progress`` anywhere in
  this module; pruning is a manual operator action (FR-035).
- A ``writeback_progress`` row in ``resume_needed`` state MUST be retained until
  the session is resumed-completed or explicitly abandoned by the operator, even
  if it predates the calendar floor.
- ``writeback_progress.last_error`` MUST NOT contain secrets or full CRM record
  contents (spec §Definitions §"Operator-visible"). The adapter's failure path
  passes a sanitized summary string. ``tests/contract/test_no_secrets_in_artifacts.py``
  greps the serialized row for known-secret env values to enforce this property.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from opencloser.models import (
    SCHEMA_VERSION,
    CallableStatus,
    ConflictingEventAuditRecord,
    CrmCorrelation,
    CrmRecordKind,
    CrmWriteStatus,
    Disposition,
    EligibilityDecision,
    EventType,
    MockCallEvent,
    NormalizedResult,
    PhoneCallActivityPayload,
    QueueItem,
    QueueStatusUpdatePayload,
    RuleCode,
    RunStatus,
    Session,
    SessionState,
    TaskPayload,
    WriteBackProgress,
)

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection, ensure the parent dir exists, and apply Slice 1 PRAGMAs.

    The DB file holds local CRM data (N5), so it is restricted to the owner (``0o600``).
    A state directory that this call creates is likewise restricted (``0o700``), which
    also shields the WAL/SHM sidecar files; a pre-existing directory is left untouched.
    chmod is best-effort: filesystems that do not support it (some network or Windows
    mounts) are logged and tolerated rather than treated as fatal.
    """
    path = Path(db_path)
    state_dir = path.parent
    # Harden the state directory only when THIS call creates it. chmod-ing a
    # pre-existing directory — the CWD for a bare filename, or any shared location an
    # absolute db_path points into — would change permissions other processes and
    # users rely on.
    created_state_dir = not state_dir.exists()
    state_dir.mkdir(parents=True, exist_ok=True)
    if created_state_dir:
        _restrict_permissions(state_dir, 0o700)
    conn = sqlite3.connect(str(path), isolation_level=None)
    _restrict_permissions(path, 0o600)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def _restrict_permissions(target: Path, mode: int) -> None:
    """Best-effort chmod restricting local CRM state to the owner (N5).

    A filesystem that does not support chmod is logged and tolerated — losing the
    permission hardening is preferable to crashing the run.
    """
    try:
        os.chmod(target, mode)
    except OSError as exc:
        _LOGGER.warning("could not restrict permissions on %s (mode %o): %s", target, mode, exc)


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run a block inside a single SQLite transaction."""
    conn.execute("BEGIN;")
    try:
        yield conn
    except Exception:
        conn.execute("ROLLBACK;")
        raise
    else:
        conn.execute("COMMIT;")


def init_schema(conn: sqlite3.Connection, *, now_utc_ms: str) -> None:
    """Apply schema.sql idempotently and seed the schema_meta row if first run."""
    ddl = _SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(ddl)
    cur = conn.execute("SELECT COUNT(*) AS n FROM schema_meta;")
    if cur.fetchone()["n"] == 0:
        conn.execute(
            "INSERT INTO schema_meta (applied_at, version) VALUES (?, ?);",
            (now_utc_ms, SCHEMA_VERSION),
        )


# ---------------------------------------------------------------------------
# QueueItem
# ---------------------------------------------------------------------------


def insert_queue_item(conn: sqlite3.Connection, item: QueueItem) -> None:
    conn.execute(
        """
        INSERT INTO queue_items (
            queue_item_id, facility_name, phone_number, timezone, default_tz_applied,
            email, attempt_count, dnc_flag, callable_status, last_decision_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            item.queue_item_id,
            item.facility_name,
            item.phone_number,
            item.timezone,
            int(item.default_tz_applied),
            item.email,
            item.attempt_count,
            int(item.dnc_flag),
            item.callable_status.value,
            item.last_decision_at,
        ),
    )


def get_queue_item(conn: sqlite3.Connection, queue_item_id: str) -> QueueItem | None:
    row = conn.execute(
        "SELECT * FROM queue_items WHERE queue_item_id = ?;", (queue_item_id,)
    ).fetchone()
    if row is None:
        return None
    return _row_to_queue_item(row)


def increment_attempt_count(conn: sqlite3.Connection, queue_item_id: str) -> None:
    """FR-021 — exactly-once-per-mock-provider-call-id increment is guarded by the
    orchestrator via idempotency_keys; this function just applies the bump."""
    conn.execute(
        "UPDATE queue_items SET attempt_count = attempt_count + 1 WHERE queue_item_id = ?;",
        (queue_item_id,),
    )


def update_queue_item_status(
    conn: sqlite3.Connection,
    queue_item_id: str,
    *,
    callable_status: CallableStatus | None = None,
    dnc_flag: bool | None = None,
    last_decision_at: str | None = None,
) -> None:
    """Partial-update DAO: `None` means "leave this column alone".

    For Slice 2's runner staging — where every mutable column on the queue row
    must mirror the live Dataverse snapshot including null clears — use
    `replace_queue_item_mutable_fields` instead.
    """
    fields: list[str] = []
    values: list[Any] = []
    if callable_status is not None:
        fields.append("callable_status = ?")
        values.append(callable_status.value)
    if dnc_flag is not None:
        fields.append("dnc_flag = ?")
        values.append(int(dnc_flag))
    if last_decision_at is not None:
        fields.append("last_decision_at = ?")
        values.append(last_decision_at)
    if not fields:
        return
    values.append(queue_item_id)
    conn.execute(
        f"UPDATE queue_items SET {', '.join(fields)} WHERE queue_item_id = ?;",
        tuple(values),
    )


def replace_queue_item_mutable_fields(
    conn: sqlite3.Connection,
    queue_item: QueueItem,
) -> None:
    """Overwrite every mutable column on the local queue row from a fresh source
    snapshot — including null clears.

    `update_queue_item_status` treats `None` as "don't update", so a Dataverse
    field that has been cleared to null since the last run never propagates to
    local state. Slice 2's runner needs the opposite semantics when re-staging
    a row read live from Dataverse: every mutable column should mirror the
    snapshot, null included, so eligibility evaluates against current state
    rather than whatever a prior run last wrote.
    """
    conn.execute(
        """
        UPDATE queue_items SET
            facility_name = ?,
            phone_number = ?,
            timezone = ?,
            default_tz_applied = ?,
            email = ?,
            attempt_count = ?,
            dnc_flag = ?,
            callable_status = ?,
            last_decision_at = ?
        WHERE queue_item_id = ?;
        """,
        (
            queue_item.facility_name,
            queue_item.phone_number,
            queue_item.timezone,
            int(queue_item.default_tz_applied),
            queue_item.email,
            queue_item.attempt_count,
            int(queue_item.dnc_flag),
            queue_item.callable_status.value,
            queue_item.last_decision_at,
            queue_item.queue_item_id,
        ),
    )


def _row_to_queue_item(row: sqlite3.Row) -> QueueItem:
    return QueueItem(
        queue_item_id=row["queue_item_id"],
        facility_name=row["facility_name"],
        phone_number=row["phone_number"],
        timezone=row["timezone"],
        default_tz_applied=bool(row["default_tz_applied"]),
        email=row["email"],
        attempt_count=row["attempt_count"],
        dnc_flag=bool(row["dnc_flag"]),
        callable_status=CallableStatus(row["callable_status"]),
        last_decision_at=row["last_decision_at"],
    )


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


def insert_session(conn: sqlite3.Connection, session: Session) -> None:
    conn.execute(
        """
        INSERT INTO sessions (
            session_id, queue_item_id, persona_version, state,
            final_disposition, blocked_reason, mock_provider_call_id, started_at, ended_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            session.session_id,
            session.queue_item_id,
            session.persona_version,
            session.state.value,
            session.final_disposition.value if session.final_disposition else None,
            json.dumps(session.blocked_reason) if session.blocked_reason else None,
            session.mock_provider_call_id,
            session.started_at,
            session.ended_at,
        ),
    )


def update_session(
    conn: sqlite3.Connection,
    session_id: str,
    *,
    state: SessionState | None = None,
    final_disposition: Disposition | None = None,
    blocked_reason: list[RuleCode] | None = None,
    mock_provider_call_id: str | None = None,
    persona_version: str | None = None,
    ended_at: str | None = None,
) -> None:
    fields: list[str] = []
    values: list[Any] = []
    if state is not None:
        fields.append("state = ?")
        values.append(state.value)
    if final_disposition is not None:
        fields.append("final_disposition = ?")
        values.append(final_disposition.value)
    if blocked_reason is not None:
        fields.append("blocked_reason = ?")
        values.append(json.dumps(blocked_reason))
    if mock_provider_call_id is not None:
        fields.append("mock_provider_call_id = ?")
        values.append(mock_provider_call_id)
    if persona_version is not None:
        fields.append("persona_version = ?")
        values.append(persona_version)
    if ended_at is not None:
        fields.append("ended_at = ?")
        values.append(ended_at)
    if not fields:
        return
    values.append(session_id)
    conn.execute(
        f"UPDATE sessions SET {', '.join(fields)} WHERE session_id = ?;",
        tuple(values),
    )


def get_session(conn: sqlite3.Connection, session_id: str) -> Session | None:
    row = conn.execute("SELECT * FROM sessions WHERE session_id = ?;", (session_id,)).fetchone()
    if row is None:
        return None
    blocked = json.loads(row["blocked_reason"]) if row["blocked_reason"] else None
    return Session(
        session_id=row["session_id"],
        queue_item_id=row["queue_item_id"],
        persona_version=row["persona_version"],
        state=SessionState(row["state"]),
        final_disposition=Disposition(row["final_disposition"])
        if row["final_disposition"]
        else None,
        blocked_reason=blocked,
        mock_provider_call_id=row["mock_provider_call_id"],
        started_at=row["started_at"],
        ended_at=row["ended_at"],
    )


# ---------------------------------------------------------------------------
# EligibilityDecision
# ---------------------------------------------------------------------------


def insert_eligibility_decision(conn: sqlite3.Connection, decision: EligibilityDecision) -> None:
    conn.execute(
        """
        INSERT INTO eligibility_decisions (
            decision_id, queue_item_id, decided_at, outcome,
            rule_a_phone_pass, rule_b_timezone_pass, rule_c_call_window_pass,
            rule_d_dnc_pass, rule_e_max_attempts_pass, rule_f_callable_status_pass,
            failing_rules, default_tz_applied, default_tz_substituted_for, session_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            decision.decision_id,
            decision.queue_item_id,
            decision.decided_at,
            decision.outcome,
            int(decision.rule_a_phone_pass),
            int(decision.rule_b_timezone_pass),
            int(decision.rule_c_call_window_pass),
            int(decision.rule_d_dnc_pass),
            int(decision.rule_e_max_attempts_pass),
            int(decision.rule_f_callable_status_pass),
            json.dumps(decision.failing_rules) if decision.failing_rules else None,
            int(decision.default_tz_applied),
            decision.default_tz_substituted_for,
            decision.session_id,
        ),
    )


# ---------------------------------------------------------------------------
# MockCallEvent
# ---------------------------------------------------------------------------


def insert_mock_call_event(conn: sqlite3.Connection, event: MockCallEvent) -> None:
    conn.execute(
        """
        INSERT INTO mock_call_events (session_id, event_id, event_type, received_at, payload_json)
        VALUES (?, ?, ?, ?, ?);
        """,
        (
            event.session_id,
            event.event_id,
            event.event_type.value,
            event.received_at,
            json.dumps(event.payload, sort_keys=True),
        ),
    )


def list_mock_call_events(conn: sqlite3.Connection, session_id: str) -> list[MockCallEvent]:
    rows = conn.execute(
        "SELECT * FROM mock_call_events WHERE session_id = ? ORDER BY received_at;",
        (session_id,),
    ).fetchall()
    return [
        MockCallEvent(
            session_id=row["session_id"],
            event_id=row["event_id"],
            event_type=EventType(row["event_type"]),
            received_at=row["received_at"],
            payload=json.loads(row["payload_json"]),
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Idempotency keys
# ---------------------------------------------------------------------------


def try_record_idempotency_key(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    mock_provider_call_id: str | None,
    event_id: str | None,
    write_back_kind: str,
    applied_at: str,
) -> bool:
    """INSERT into idempotency_keys; return True if the key is new (caller should proceed),
    False if it already exists (caller should treat as duplicate no-op per FR-019)."""
    try:
        conn.execute(
            """
            INSERT INTO idempotency_keys (session_id, mock_provider_call_id, event_id, write_back_kind, applied_at)
            VALUES (?, ?, ?, ?, ?);
            """,
            (session_id, mock_provider_call_id or "", event_id or "", write_back_kind, applied_at),
        )
    except sqlite3.IntegrityError as exc:
        # A PRIMARY KEY (or UNIQUE) conflict means the key was already recorded — the
        # FR-019 duplicate no-op. Any other integrity failure (FK, CHECK, NOT NULL) is a
        # real bug and must surface rather than be downgraded to a silent skip.
        if exc.sqlite_errorname in ("SQLITE_CONSTRAINT_PRIMARYKEY", "SQLITE_CONSTRAINT_UNIQUE"):
            return False
        raise
    return True


# ---------------------------------------------------------------------------
# Conflicting late event audit
# ---------------------------------------------------------------------------


def insert_conflicting_event(conn: sqlite3.Connection, audit: ConflictingEventAuditRecord) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO conflicting_event_audit_records (
            audit_id, session_id, event_id, conflicting_event_type,
            received_at, full_event_payload_json, preserved_disposition
        ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        (
            audit.audit_id,
            audit.session_id,
            audit.event_id,
            audit.conflicting_event_type.value,
            audit.received_at,
            json.dumps(audit.full_event_payload, sort_keys=True),
            audit.preserved_disposition.value,
        ),
    )


def list_conflicting_events(
    conn: sqlite3.Connection, session_id: str
) -> list[ConflictingEventAuditRecord]:
    rows = conn.execute(
        "SELECT * FROM conflicting_event_audit_records WHERE session_id = ? ORDER BY received_at;",
        (session_id,),
    ).fetchall()
    return [
        ConflictingEventAuditRecord(
            audit_id=row["audit_id"],
            session_id=row["session_id"],
            event_id=row["event_id"],
            conflicting_event_type=EventType(row["conflicting_event_type"]),
            received_at=row["received_at"],
            full_event_payload=json.loads(row["full_event_payload_json"]),
            preserved_disposition=Disposition(row["preserved_disposition"]),
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Write-back payloads
# ---------------------------------------------------------------------------


def insert_phone_call_activity(conn: sqlite3.Connection, payload: PhoneCallActivityPayload) -> None:
    conn.execute(
        """
        INSERT INTO phone_call_activities (
            session_id, queue_item_id, mock_provider_call_id, persona_version,
            final_disposition, summary, started_at, ended_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            payload.session_id,
            payload.queue_item_id,
            payload.mock_provider_call_id,
            payload.persona_version,
            payload.final_disposition.value,
            payload.summary,
            payload.started_at,
            payload.ended_at,
        ),
    )


def insert_queue_status_update(conn: sqlite3.Connection, payload: QueueStatusUpdatePayload) -> None:
    conn.execute(
        """
        INSERT INTO queue_status_updates (
            session_id, queue_item_id, previous_status, new_status, transition_reason, transition_at
        ) VALUES (?, ?, ?, ?, ?, ?);
        """,
        (
            payload.session_id,
            payload.queue_item_id,
            payload.previous_status.value,
            payload.new_status.value,
            payload.transition_reason,
            payload.transition_at,
        ),
    )


def insert_task_payload(conn: sqlite3.Connection, payload: TaskPayload) -> None:
    conn.execute(
        """
        INSERT INTO task_payloads (
            task_id, session_id, queue_item_id, task_kind, subject,
            reason_code, preferred_callback_window, captured_email, assigned_to,
            persona_version, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            payload.task_id,
            payload.session_id,
            payload.queue_item_id,
            payload.task_kind,
            payload.subject,
            payload.reason_code.value if payload.reason_code else None,
            payload.preferred_callback_window,
            payload.captured_email,
            payload.assigned_to,
            payload.persona_version,
            payload.created_at,
        ),
    )


def insert_normalized_result(conn: sqlite3.Connection, result: NormalizedResult) -> None:
    conn.execute(
        """
        INSERT INTO normalized_results (
            session_id, queue_item_id, mock_provider_call_id, persona_version,
            final_disposition, summary, transcript_pointer,
            captured_email, captured_email_unverified,
            callback_requested, preferred_callback_window, human_review_reason, blocked_reason,
            started_at, ended_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            result.session_id,
            result.queue_item_id,
            result.mock_provider_call_id,
            result.persona_version,
            result.final_disposition.value,
            result.summary,
            result.transcript_pointer,
            result.captured_email,
            result.captured_email_unverified,
            int(result.callback_requested),
            result.preferred_callback_window,
            result.human_review_reason.value if result.human_review_reason else None,
            json.dumps(result.blocked_reason) if result.blocked_reason else None,
            result.started_at,
            result.ended_at,
        ),
    )


# ---------------------------------------------------------------------------
# Slice 2 — CRM correlation + write-back progress (data-model.md §1)
# ---------------------------------------------------------------------------


def upsert_crm_correlation(conn: sqlite3.Connection, corr: CrmCorrelation) -> None:
    """FR-024 — record or refresh the local correlation row for one CRM record kind."""
    conn.execute(
        """
        INSERT INTO crm_correlations (
            session_id, record_kind, idempotency_key, dataverse_record_id,
            write_status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (session_id, record_kind) DO UPDATE SET
            idempotency_key = excluded.idempotency_key,
            dataverse_record_id = excluded.dataverse_record_id,
            write_status = excluded.write_status,
            updated_at = excluded.updated_at;
        """,
        (
            corr.session_id,
            corr.record_kind.value,
            corr.idempotency_key,
            corr.dataverse_record_id,
            corr.write_status.value,
            corr.created_at,
            corr.updated_at,
        ),
    )


def get_crm_correlation(
    conn: sqlite3.Connection, session_id: str, record_kind: CrmRecordKind
) -> CrmCorrelation | None:
    row = conn.execute(
        "SELECT * FROM crm_correlations WHERE session_id = ? AND record_kind = ?;",
        (session_id, record_kind.value),
    ).fetchone()
    return _row_to_crm_correlation(row) if row is not None else None


def list_crm_correlations(conn: sqlite3.Connection, session_id: str) -> list[CrmCorrelation]:
    rows = conn.execute(
        "SELECT * FROM crm_correlations WHERE session_id = ? ORDER BY record_kind;",
        (session_id,),
    ).fetchall()
    return [_row_to_crm_correlation(row) for row in rows]


def _row_to_crm_correlation(row: sqlite3.Row) -> CrmCorrelation:
    return CrmCorrelation(
        session_id=row["session_id"],
        record_kind=CrmRecordKind(row["record_kind"]),
        idempotency_key=row["idempotency_key"],
        dataverse_record_id=row["dataverse_record_id"],
        write_status=CrmWriteStatus(row["write_status"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def upsert_writeback_progress(conn: sqlite3.Connection, progress: WriteBackProgress) -> None:
    """FR-023 — record or refresh the per-session write-back resume ledger."""
    conn.execute(
        """
        INSERT INTO writeback_progress (
            session_id, phone_call_activity_done, queue_status_update_done,
            task_done, run_status, last_error, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (session_id) DO UPDATE SET
            phone_call_activity_done = excluded.phone_call_activity_done,
            queue_status_update_done = excluded.queue_status_update_done,
            task_done = excluded.task_done,
            run_status = excluded.run_status,
            last_error = excluded.last_error,
            updated_at = excluded.updated_at;
        """,
        (
            progress.session_id,
            int(progress.phone_call_activity_done),
            int(progress.queue_status_update_done),
            int(progress.task_done),
            progress.run_status.value,
            progress.last_error,
            progress.updated_at,
        ),
    )


def get_writeback_progress(conn: sqlite3.Connection, session_id: str) -> WriteBackProgress | None:
    row = conn.execute(
        "SELECT * FROM writeback_progress WHERE session_id = ?;", (session_id,)
    ).fetchone()
    if row is None:
        return None
    return WriteBackProgress(
        session_id=row["session_id"],
        phone_call_activity_done=bool(row["phone_call_activity_done"]),
        queue_status_update_done=bool(row["queue_status_update_done"]),
        task_done=bool(row["task_done"]),
        run_status=RunStatus(row["run_status"]),
        last_error=row["last_error"],
        updated_at=row["updated_at"],
    )
