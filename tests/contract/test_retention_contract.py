"""T041 — Retention enforcement contract (FR-023, FR-035).

Asserts the no-auto-delete property the spec edits added in 2026-05-24
(FR-035: "local audit artifacts and FR-023 correlation/progress rows MUST
NOT be auto-deleted by the application; pruning is a manual operator
action"):

  * ``src/opencloser/state/store.py`` contains ZERO SQL DELETE statements
    against ``crm_correlations`` or ``writeback_progress``.
  * ``src/opencloser/artifacts/writer.py`` contains no filesystem-delete
    call (``unlink``, ``rmtree``, etc.) targeting session artifacts beyond
    the documented exceptions: the FR-030 summary-only transcript sweep
    and the failed-atomic-write tempfile cleanup.

Plus a behavioral test: an old `writeback_progress` row (predating the
calendar floor) and an old `crm_correlations` row remain readable — no
implicit purging happens on schema init, session insertion, or DAO calls.

Complements ``tests/contract/test_no_secrets_in_artifacts.py`` (T047), which
covers the no-secrets-retained aspect of the same retention contract.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from opencloser.models import (
    CrmCorrelation,
    CrmRecordKind,
    CrmWriteStatus,
    RunStatus,
    WriteBackProgress,
)
from opencloser.state import store

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src" / "opencloser"


# ---------------------------------------------------------------------------
# Static — no-DELETE-against-retention-tables and no-unlink-of-audit-artifacts
# ---------------------------------------------------------------------------


def test_store_has_no_delete_against_retention_protected_tables() -> None:
    """FR-035 / T041 — `store.py` contains ZERO SQL DELETE statements against
    `crm_correlations` or `writeback_progress`. The application MUST NOT
    auto-delete these rows; pruning is a manual operator action."""
    text = (_SRC / "state" / "store.py").read_text(encoding="utf-8")
    forbidden = (
        re.compile(r"DELETE\s+FROM\s+crm_correlations", re.IGNORECASE),
        re.compile(r"DELETE\s+FROM\s+writeback_progress", re.IGNORECASE),
    )
    leaks = [pat.pattern for pat in forbidden if pat.search(text)]
    assert not leaks, (
        f"src/opencloser/state/store.py contains forbidden DELETE statement(s): "
        f"{leaks}. FR-035 forbids auto-deletion of FR-023 retention-protected rows."
    )


def test_writer_has_no_audit_artifact_deletion_beyond_documented_exceptions() -> None:
    """FR-035 / T041 — `artifacts/writer.py` contains no filesystem-delete
    call against audit artifacts beyond the two documented exceptions:

      1. The FR-030 summary-only transcript sweep
         (``(session_dir / _TRANSCRIPT_FILENAME).unlink(missing_ok=True)``).
      2. The failed-atomic-write tempfile cleanup
         (``os.unlink(tmp_name)`` after a partial tempfile write).

    Pass 3 (2026-05-24 audit-remediation): walks the AST instead of grepping
    text so docstring examples that mention `.unlink(` don't trip the test.
    """
    import ast

    tree = ast.parse((_SRC / "artifacts" / "writer.py").read_text(encoding="utf-8"))
    deletion_call_names: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # Match `<expr>.unlink(...)`, `os.unlink(...)`, `os.remove(...)`,
        # `shutil.rmtree(...)` — every shape of filesystem deletion call.
        if isinstance(func, ast.Attribute) and func.attr in {
            "unlink", "remove", "rmtree"
        }:
            deletion_call_names.append(func.attr)

    # Both documented exceptions are non-vendor — they're privacy + cleanup.
    # The total count is 2 today; if a future change adds a new deletion, this
    # test fails and the author must justify (and document) the addition.
    assert len(deletion_call_names) == 2, (
        f"artifacts/writer.py has {len(deletion_call_names)} deletion call(s) "
        f"{deletion_call_names!r}; expected exactly 2 (the FR-030 transcript "
        f"sweep `.unlink` + the atomic-write tempfile cleanup `os.unlink`). "
        f"New deletion calls violate the FR-035 no-auto-delete contract — "
        f"document and add a justification before raising this count."
    )


# ---------------------------------------------------------------------------
# Behavioral — old rows remain readable; no implicit purge happens
# ---------------------------------------------------------------------------


_OLD_TS = "2024-01-01T00:00:00.000Z"  # Well past any 90-day floor from "today".
_NEW_TS = "2026-05-24T19:00:00.000Z"


def _seed_session(conn: sqlite3.Connection, session_id: str, queue_item_id: str) -> None:
    """Minimal-FK seed: queue_item + session row so we can attach the
    retention-protected rows below. The session row is what crm_correlations
    + writeback_progress FK-reference."""
    from opencloser.models import (
        CallableStatus,
        QueueItem,
        Session,
        SessionState,
    )

    with store.transaction(conn):
        store.insert_queue_item(
            conn,
            QueueItem(
                queue_item_id=queue_item_id,
                facility_name="Sunage ALF",
                phone_number="+15305551234",
                timezone="America/Los_Angeles",
                attempt_count=0,
                callable_status=CallableStatus.READY,
            ),
        )
        store.insert_session(
            conn,
            Session(
                session_id=session_id,
                queue_item_id=queue_item_id,
                state=SessionState.FINALIZED,
                final_disposition=None,
                started_at=_OLD_TS,
                ended_at=_OLD_TS,
            ),
        )


def test_old_crm_correlation_row_remains_readable(
    tmp_state_db: sqlite3.Connection,
) -> None:
    """FR-023 / T041 — a `crm_correlations` row dated 2024 (well past any
    90-day floor) is readable verbatim. No DAO call purges it implicitly."""
    sid = "ses_retention_test_old_crm"
    qid = "q_retention_test_old_crm"
    _seed_session(tmp_state_db, sid, qid)

    with store.transaction(tmp_state_db):
        store.upsert_crm_correlation(
            tmp_state_db,
            CrmCorrelation(
                session_id=sid,
                record_kind=CrmRecordKind.PHONE_CALL_ACTIVITY,
                idempotency_key=sid,
                dataverse_record_id="00000000-0000-0000-0000-000000000099",
                write_status=CrmWriteStatus.CONFIRMED,
                created_at=_OLD_TS,
                updated_at=_OLD_TS,
            ),
        )

    # A second DAO call (the typical resume-time inspection) MUST NOT purge it.
    rows = store.list_crm_correlations(tmp_state_db, sid)
    assert len(rows) == 1
    assert rows[0].created_at == _OLD_TS, "stale row was rewritten/purged"
    assert rows[0].dataverse_record_id == "00000000-0000-0000-0000-000000000099"


def test_old_writeback_progress_row_remains_readable(
    tmp_state_db: sqlite3.Connection,
) -> None:
    """FR-023 / T041 — a `writeback_progress` row in `resume_needed` state
    dated 2024 remains readable. The spec MUST retain `resume_needed` rows
    until resumed-completed or explicitly abandoned, even past the calendar
    floor."""
    sid = "ses_retention_test_old_progress"
    qid = "q_retention_test_old_progress"
    _seed_session(tmp_state_db, sid, qid)

    with store.transaction(tmp_state_db):
        store.upsert_writeback_progress(
            tmp_state_db,
            WriteBackProgress(
                session_id=sid,
                phone_call_activity_done=True,
                queue_status_update_done=False,
                task_done=False,
                run_status=RunStatus.RESUME_NEEDED,
                last_error="simulated transient exhaust (T041 retention test)",
                updated_at=_OLD_TS,
            ),
        )

    row = store.get_writeback_progress(tmp_state_db, sid)
    assert row is not None
    assert row.run_status is RunStatus.RESUME_NEEDED
    assert row.updated_at == _OLD_TS, "stale resume_needed row was purged or rewritten"


def test_recent_row_does_not_clobber_old_row(
    tmp_state_db: sqlite3.Connection,
) -> None:
    """A new run for a different session MUST NOT purge an older session's
    retention-protected rows."""
    old_sid = "ses_retention_old"
    old_qid = "q_retention_old"
    new_sid = "ses_retention_new"
    new_qid = "q_retention_new"

    _seed_session(tmp_state_db, old_sid, old_qid)
    _seed_session(tmp_state_db, new_sid, new_qid)

    with store.transaction(tmp_state_db):
        store.upsert_writeback_progress(
            tmp_state_db,
            WriteBackProgress(
                session_id=old_sid,
                phone_call_activity_done=True,
                queue_status_update_done=True,
                task_done=True,
                run_status=RunStatus.COMPLETED,
                last_error=None,
                updated_at=_OLD_TS,
            ),
        )
        store.upsert_writeback_progress(
            tmp_state_db,
            WriteBackProgress(
                session_id=new_sid,
                phone_call_activity_done=True,
                queue_status_update_done=True,
                task_done=True,
                run_status=RunStatus.COMPLETED,
                last_error=None,
                updated_at=_NEW_TS,
            ),
        )

    # The old row's updated_at is unchanged.
    old_row = store.get_writeback_progress(tmp_state_db, old_sid)
    assert old_row is not None and old_row.updated_at == _OLD_TS

    # And the new row coexists.
    new_row = store.get_writeback_progress(tmp_state_db, new_sid)
    assert new_row is not None and new_row.updated_at == _NEW_TS


def test_schema_init_does_not_purge_existing_rows(
    tmp_state_db: sqlite3.Connection,
) -> None:
    """Calling `init_schema` a second time (idempotent re-init that happens on
    every `connect`) MUST NOT delete any retention-protected row. The schema
    uses `CREATE TABLE IF NOT EXISTS` and there is no explicit purge."""
    sid = "ses_retention_test_reinit"
    qid = "q_retention_test_reinit"
    _seed_session(tmp_state_db, sid, qid)
    with store.transaction(tmp_state_db):
        store.upsert_crm_correlation(
            tmp_state_db,
            CrmCorrelation(
                session_id=sid,
                record_kind=CrmRecordKind.QUEUE_STATUS,
                idempotency_key=sid,
                dataverse_record_id="00000000-0000-0000-0000-000000000abc",
                write_status=CrmWriteStatus.CONFIRMED,
                created_at=_OLD_TS,
                updated_at=_OLD_TS,
            ),
        )

    # Re-init the schema (this is what `connect` does on every open).
    store.init_schema(tmp_state_db, now_utc_ms=datetime.now(UTC).isoformat())

    rows = store.list_crm_correlations(tmp_state_db, sid)
    assert len(rows) == 1, "schema re-init purged retention-protected rows"
