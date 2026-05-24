"""Slice 2 resume coordinator (FR-023, FR-014).

When a write-enabled run exhausts its retry budget mid-write-back the runner
exits with ``run_status = resume_needed`` and persists three things:

1. ``writeback_progress(session_id, phone_call_activity_done,
   queue_status_update_done, task_done, run_status)`` — which of the three
   write-back ops succeeded.
2. ``writeback.json`` (under ``<artifact_root>/<session_id>/``) — the
   conceptual payloads the run intended to emit; written atomically per the
   Slice 1 artifact contract.
3. ``crm_correlations`` rows — the confirmed CRM record IDs and any
   ``failed`` rows from the partial run, so a later resume's pre-query
   short-circuits cleanly even if a record was created but the local
   correlation row was rolled back by a transient error.

``resume_session`` rebuilds an adapter, loads (1) + (2), and replays ONLY the
``emit_*`` operations the progress row reports as not-done. The adapter's
existing ``_idempotent_create`` pre-query (FR-024) provides belt-and-suspenders:
if a record WAS created in the partial run but ``_record_correlation`` never
committed, the pre-query still finds it by idempotency key and the resume
reuses the existing CRM record ID — no duplicate Phone Call activity or Task
gets created (SC-005, SC-014).

The Slice 1 orchestrator is intentionally NOT re-invoked (FR-014 — resume
completes only the missing CRM writes, not the eligibility/persona loop).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from opencloser.core.clock import Clock, SystemClock
from opencloser.crm.dataverse.adapter import DataverseWriteBackAdapter, DataverseWriteBackError
from opencloser.crm.dataverse.client import DataverseClient
from opencloser.crm.dataverse.errors import DataverseError
from opencloser.crm.dataverse.mapping import MappingError, MappingTranslator
from opencloser.models import (
    RunStatus,
    TaskOwnersConfig,
    WriteBack,
)
from opencloser.state import store

_WRITEBACK_FILENAME = "writeback.json"


@dataclass
class ResumeReport:
    """The resume coordinator's outcome — superset of CrmRunReport.

    The slice2 runner converts this to a CrmRunReport when called from the CLI.
    """

    exit_status: str  # "completed" | "failed" | "blocked" | "no-resume-needed"
    session_id: str
    message: str | None = None
    artifact_dir: Path | None = None
    operations_replayed: list[str] | None = None


class ResumeError(RuntimeError):
    """Pre-flight resume failure (writeback.json missing, progress row absent,
    session not in resume_needed state). Distinct from a Dataverse write
    failure during replay, which produces a ``failed`` ResumeReport."""


def resume_session(
    *,
    session_id: str,
    conn: sqlite3.Connection,
    artifact_root: Path,
    client: DataverseClient,
    translator: MappingTranslator,
    task_owners: TaskOwnersConfig,
    clock: Clock | None = None,
) -> ResumeReport:
    """Replay only the missing ``emit_*`` operations for a ``resume_needed``
    session. Returns a ``ResumeReport`` describing the outcome.

    FR-023 — does NOT re-run ``process_one_queue_item``. The resume operates
    purely on the persisted ``writeback.json`` payloads and the
    ``writeback_progress`` flags; eligibility, persona, transport, and the
    session lifecycle are unchanged.
    """
    clk = clock or SystemClock()

    progress = store.get_writeback_progress(conn, session_id)
    if progress is None:
        raise ResumeError(
            f"session {session_id!r} has no writeback_progress row; nothing to resume"
        )
    if progress.run_status is not RunStatus.RESUME_NEEDED:
        return ResumeReport(
            exit_status="no-resume-needed",
            session_id=session_id,
            message=(
                f"session is in {progress.run_status.value!r}, not 'resume_needed'; "
                "no replay performed"
            ),
        )

    # Load the persisted WriteBack payloads. The Slice 1 artifact writer
    # always emits writeback.json atomically; its presence is part of the
    # resume contract per FR-023.
    session_dir = artifact_root / session_id
    writeback_path = session_dir / _WRITEBACK_FILENAME
    if not writeback_path.exists():
        raise ResumeError(
            f"writeback.json missing under {session_dir!r}; cannot resume "
            "without persisted payloads (FR-023). Inspect local audit-artifact "
            "retention (FR-035) and re-run the original `run-crm` instead."
        )
    writeback = WriteBack.model_validate_json(
        writeback_path.read_text(encoding="utf-8")
    )

    # Build a fresh adapter. dry_run=False because resume is a write-enabled
    # operation by definition (FR-023 — completes the missing writes).
    adapter = DataverseWriteBackAdapter(
        conn=conn,
        client=client,
        translator=translator,
        task_owners=task_owners,
        now_utc_ms=clk.now_utc_ms,
    )

    replayed: list[str] = []
    try:
        # Phone Call activity — replay only if not already done. The adapter's
        # _idempotent_create still pre-queries by idempotency key, so if the
        # record WAS created in the partial run but the local correlation row
        # was rolled back, the existing CRM record is reused (FR-024).
        if not progress.phone_call_activity_done and writeback.phone_call_activity is not None:
            adapter.emit_phone_call_activity(writeback.phone_call_activity)
            replayed.append("phone_call_activity")

        # Queue status update — replay only if not already done. The adapter's
        # _fetch_queue_last_session check skips the PATCH if the row already
        # carries this session's id.
        if not progress.queue_status_update_done:
            adapter.emit_queue_status_update(writeback.queue_status_update)
            replayed.append("queue_status_update")

        # Task — replay only if not already done. emit_task's FR-018 exclusion
        # path will skip the operation if the session's final_disposition is in
        # the no-task set; otherwise pre-query + create or reuse.
        if not progress.task_done and writeback.task is not None:
            adapter.emit_task(writeback.task)
            replayed.append("task")
    except (DataverseError, DataverseWriteBackError, MappingError) as exc:
        # The replay itself failed (transient exhausted again, mapping
        # invalidated, permission regression, etc.). Persist staged failures
        # exactly as the write-enabled runner does, leaving the session in a
        # state another resume invocation can pick up if appropriate.
        adapter.flush_pending_failures()
        return ResumeReport(
            exit_status="failed",
            session_id=session_id,
            message=f"resume replay failed: {exc}",
            artifact_dir=session_dir,
            operations_replayed=replayed,
        )

    # Every replay succeeded. Stamp the terminal progress row so a third
    # invocation sees `completed` and short-circuits via the
    # no-resume-needed path above.
    adapter.finalize_progress(session_id, run_status=RunStatus.COMPLETED)
    return ResumeReport(
        exit_status="completed",
        session_id=session_id,
        message=(
            f"resume completed; replayed {len(replayed)} operation(s): "
            f"{', '.join(replayed) or 'none'}"
        ),
        artifact_dir=session_dir,
        operations_replayed=replayed,
    )


__all__ = ("ResumeError", "ResumeReport", "resume_session")
