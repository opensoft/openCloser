"""Slice 2 resume coordinator (FR-023, FR-014).

When a write-enabled run exhausts its retry budget mid-write-back the runner
exits with ``run_status = resume_needed`` and persists:

1. ``writeback_progress(session_id, phone_call_activity_done,
   queue_status_update_done, task_done, run_status)`` — which of the three
   write-back ops succeeded.
2. ``crm_correlations`` rows — the confirmed CRM record IDs and any
   ``failed`` rows from the partial run, so a later resume's pre-query
   short-circuits cleanly even if a record was created but the local
   correlation row was rolled back by a transient error.

``resume_session`` rebuilds an adapter, loads (1) + the persisted
``writeback.json`` artifact, and replays ONLY the ``emit_*`` operations the
progress row reports as not-done. The adapter's existing
``_idempotent_create`` pre-query (FR-024) provides belt-and-suspenders: if a
record WAS created in the partial run but ``_record_correlation`` never
committed, the pre-query still finds it by idempotency key and the resume
reuses the existing CRM record ID — no duplicate Phone Call activity or Task
gets created (SC-005, SC-014).

The Slice 1 orchestrator is intentionally NOT re-invoked (FR-014 — resume
completes only the missing CRM writes, not the eligibility/persona loop).

KNOWN LIMITATION (Copilot PR #9 round-2 P1):
   The Slice 1 orchestrator writes ``writeback.json`` only AFTER all
   ``emit_*`` operations succeed. So a write-enabled run that exits
   ``resume_needed`` due to a transient mid-emit failure has NO
   ``writeback.json`` to replay from, and ``resume_session`` will raise
   ``ResumeError("writeback.json missing …")``. The current resume path
   therefore works for synthesized resume_needed states (tests +
   operator-staged scenarios) but cannot recover natural transient-exhaust
   failures end-to-end without an orchestrator-side change to persist the
   planned WriteBack incrementally (e.g. an early "planned-writeback.json"
   sidecar before emit_* attempts). Tracked as a follow-up; the resume
   coordinator's design is correct and the architectural fix is
   independent of US4 scope.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from opencloser.core.clock import Clock, SystemClock
from opencloser.crm.dataverse.adapter import (
    CrmConflictError,
    DataverseWriteBackAdapter,
    DataverseWriteBackError,
)
from opencloser.crm.dataverse.client import DataverseClient
from opencloser.crm.dataverse.errors import DataverseError, TransientDataverseError
from opencloser.crm.dataverse.mapping import MappingError, MappingTranslator
from opencloser.crm.dataverse.queue_loader import (
    DataverseQueueLoader,
    ExplicitId,
    QueueLoadError,
)
from opencloser.models import (
    RunStatus,
    TaskOwnersConfig,
    WriteBack,
)
from opencloser.state import store

_WRITEBACK_FILENAME = "writeback.json"


@dataclass
class ResumeReport:
    """The resume coordinator's outcome — surfaced directly to the CLI by
    ``_run_crm_resume`` (Copilot PR #9 round-2: the slice2 runner is NOT
    in the resume path; an earlier draft of this docstring incorrectly
    described a "converted to CrmRunReport" step that does not exist).

    ``exit_status`` is one of (also mapped to CLI exit codes in
    ``cli._run_crm_resume``):

      * ``"completed"`` — every missing emit_* replayed successfully (exit 0)
      * ``"no-resume-needed"`` — the session was already in COMPLETED state;
        this is the FR-021 idempotent re-invocation (exit 0)
      * ``"resume_needed"`` — the replay itself re-exhausted the retry
        budget; the session is still resumable on another invocation (exit 2)
      * ``"blocked"`` — the session is in BLOCKED state (permanent error
        from a prior run), or the replay failed with a permanent error
        and was escalated to BLOCKED (exit 1)
      * ``"failed"`` — the session is in IN_PROGRESS (refuse to race) or
        another resume pre-condition failed (exit 2)
    """

    exit_status: str
    session_id: str
    message: str | None = None
    artifact_dir: Path | None = None
    operations_replayed: list[str] | None = None
    # Pass 1C (2026-05-24 audit-remediation) — same structured discriminator
    # as CrmRunReport.block_reason. Populated for `exit_status="blocked"`
    # exits so the CLI / future run-report.json writer can branch on a typed
    # field. Values: "eligibility" | "metadata" | "conflict_detected" |
    # "permanent_other". None for non-blocked exits.
    block_reason: str | None = None


class ResumeError(RuntimeError):
    """Pre-flight resume failure that CANNOT produce a structured
    ``ResumeReport`` — there's no session to attach the report to or the
    persisted state is unreadable. Currently raised only for:

      * ``session_id`` has no ``writeback_progress`` row (the session is
        unknown to this state DB), or
      * the persisted ``writeback.json`` is missing or unreadable/malformed
        (the resume coordinator cannot replay payloads it can't load).

    Distinct from non-RESUME_NEEDED states (COMPLETED / BLOCKED /
    IN_PROGRESS) which produce a structured ``ResumeReport`` rather than
    raising — Copilot PR #9 round-3 caught the docstring claiming
    otherwise.

    Distinct from a Dataverse write failure during the replay itself,
    which also produces a structured ``ResumeReport`` (with exit_status
    ``resume_needed`` or ``blocked`` depending on the failure mode).
    """


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
    # Pass 2A (2026-05-24 audit-remediation) — exhaustive `match` over every
    # `RunStatus` value so a future addition fails noisily instead of silently
    # falling through to the replay path. Each non-RESUME_NEEDED state has a
    # distinct operator-visible outcome per the cli-slice2.md state-machine
    # contract.
    match progress.run_status:
        case RunStatus.COMPLETED:
            return ResumeReport(
                exit_status="no-resume-needed",
                session_id=session_id,
                message="session is already completed; no replay performed (FR-021)",
            )
        case RunStatus.BLOCKED:
            return ResumeReport(
                exit_status="blocked",
                session_id=session_id,
                # Pre-existing-blocked surfaces under `permanent_other` since
                # the original block_reason isn't persisted on writeback_progress
                # yet. Future enhancement: add a block_reason column to the table.
                block_reason="permanent_other",
                message=(
                    f"session {session_id!r} is in 'blocked' — a permanent error "
                    "stopped the original run. Resume cannot recover; inspect the "
                    "writeback_progress.last_error and re-discover the mapping or "
                    "manually reconcile before re-running."
                ),
            )
        case RunStatus.IN_PROGRESS:
            return ResumeReport(
                exit_status="failed",
                session_id=session_id,
                message=(
                    f"session {session_id!r} is in 'in_progress' — another run "
                    "may still be working on it (or the previous run crashed "
                    "mid-write). Refuse to replay rather than racing; investigate "
                    "the writeback_progress.updated_at timestamp."
                ),
            )
        case RunStatus.RESUME_NEEDED:
            pass  # Continue with the replay below.
        case _:  # pragma: no cover — exhaustiveness gate against future RunStatus additions
            raise ResumeError(
                f"unsupported run_status {progress.run_status!r} for session "
                f"{session_id!r}; resume coordinator must be updated for the new state"
            )

    # Load the persisted WriteBack payloads. The Slice 1 artifact writer
    # always emits writeback.json atomically; its presence is part of the
    # resume contract per FR-023. Both missing-file AND
    # malformed-content cases surface as ResumeError so the CLI handler
    # reports them uniformly (Codex PR #9 P2: previously a malformed
    # writeback.json raised ValidationError out of resume_session as an
    # unhandled exception, bypassing the structured ResumeError surface).
    session_dir = artifact_root / session_id
    writeback_path = session_dir / _WRITEBACK_FILENAME
    if not writeback_path.exists():
        raise ResumeError(
            f"writeback.json missing under {session_dir!r}; cannot resume "
            "without persisted payloads (FR-023). Inspect local audit-artifact "
            "retention (FR-035) and re-run the original `run-crm` instead."
        )
    try:
        writeback = WriteBack.model_validate_json(
            writeback_path.read_text(encoding="utf-8")
        )
    except (ValueError, OSError) as exc:
        # Pydantic's ValidationError is a ValueError subclass; OSError catches
        # truncated/locked files that read_text might surface as IOError.
        raise ResumeError(
            f"writeback.json under {session_dir!r} is malformed or unreadable "
            f"({type(exc).__name__}): {exc}. Cannot resume safely; re-run the "
            "original `run-crm` instead."
        ) from exc

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

        # T045 — fresh baseline at resume start. The original-run baseline is
        # in-memory only (not persisted), so the resume captures its own
        # snapshot of the queue row. This protects the window between
        # resume start and the final queue-status PATCH against human-driven
        # changes, mirroring the initial-run conflict-stop semantics (CHK061).
        # A re-detected conflict re-enters the T045 path: the adapter raises
        # CrmConflictError (a DataverseWriteBackError subclass) and the
        # broader except below maps it to RunStatus.BLOCKED + exit_status="blocked"
        # — never RESUME_NEEDED, since conflict-stop is permanent per spec
        # §Definitions §Permanent Dataverse error.
        if not progress.queue_status_update_done:
            _snapshot_resume_baseline(
                adapter=adapter,
                client=client,
                translator=translator,
                queue_item_id=writeback.queue_status_update.queue_item_id,
                clk=clk,
            )

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
    except (
        DataverseError, DataverseWriteBackError, MappingError, QueueLoadError
    ) as exc:
        # The replay itself failed. Distinguish transient (retry budget
        # exhausted again — leave the session resumable so a third
        # invocation can pick it up later) from permanent (mapping invalid,
        # permission regression — escalate to BLOCKED so the operator must
        # intervene). Codex PR #9 P1: previously this path always called
        # flush_pending_failures() with the default BLOCKED, which made
        # resumed sessions permanently non-resumable on any transient.
        # QueueLoadError added (Codex PR #3 P2 post-swarm): after Pass 1B
        # made `_snapshot_resume_baseline` re-raise mapping/queue-load
        # failures, the prior catch tuple let `QueueLoadError` escape
        # uncaught — now routed to BLOCKED (it's a permanent mapping /
        # data-drift failure, not a transient blip).
        failure_run_status = (
            RunStatus.RESUME_NEEDED
            if isinstance(exc, TransientDataverseError)
            else RunStatus.BLOCKED
        )
        adapter.flush_pending_failures(failure_run_status=failure_run_status)
        # Map the persisted progress state to the ResumeReport exit_status so
        # the CLI exit-code mapping (resume_needed→2, blocked→1, failed→2)
        # matches what landed in writeback_progress. Copilot PR #9 round-3
        # caught the BLOCKED → "failed" mismatch — `flush_pending_failures`
        # stamped run_status=BLOCKED but we previously returned
        # exit_status="failed", which is exit 2 instead of the documented
        # blocked→exit 1.
        if failure_run_status is RunStatus.RESUME_NEEDED:
            exit_status = "resume_needed"
        elif failure_run_status is RunStatus.BLOCKED:
            exit_status = "blocked"
        else:  # pragma: no cover — failure_run_status is currently always one of the above
            exit_status = "failed"
        # Distinguish T045 conflict-on-resume from other permanent errors so
        # the operator-visible discriminator matches the initial-run path.
        block_reason: str | None = None
        if exit_status == "blocked":
            block_reason = (
                "conflict_detected"
                if isinstance(exc, CrmConflictError)
                else "permanent_other"
            )
        return ResumeReport(
            exit_status=exit_status,
            session_id=session_id,
            message=f"resume replay failed: {exc}",
            artifact_dir=session_dir,
            operations_replayed=replayed,
            block_reason=block_reason,
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


def _snapshot_resume_baseline(
    *,
    adapter: DataverseWriteBackAdapter,
    client: DataverseClient,
    translator: MappingTranslator,
    queue_item_id: str,
    clk: Clock,
) -> None:
    """T045 / CHK061 — snapshot the queue row at resume start and register it
    on the adapter so the conflict-check in ``emit_queue_status_update`` fires
    on the resume path too.

    Failure-handling (Pass 1B + Codex PR #3 P2 post-swarm, 2026-05-24): the
    prior bare ``except (MappingError, QueueLoadError, DataverseError):
    return`` silently bypassed the conflict-stop on resume — a transient /
    mapping failure during the snapshot left ``_baseline = None`` and the
    subsequent ``emit_queue_status_update`` PATCHed without conflict
    detection, overwriting any human change during the pause window. Now:

      * ``MappingError`` / ``QueueLoadError`` re-raise → permanent error;
        the outer ``resume_session`` except routes to ``RunStatus.BLOCKED``
        (``block_reason="permanent_other"``).
      * ``DataverseError`` re-raises → ``TransientDataverseError`` routes to
        ``RESUME_NEEDED`` (operator can re-invoke), ``PermanentDataverseError``
        routes to ``BLOCKED``.
      * The "row not found" case (``loaded is None``) — i.e. the queue
        record was deleted during the pause window — raises
        ``CrmConflictError(["__row_deleted__"])`` so the resume path
        symmetrically produces ``blocked / conflict_detected`` (same shape
        as the initial-run path: see ``adapter._check_conflict``).
        Previously this was a silent skip that deferred the signal to a
        downstream 404 → ``permanent_other``, masking the conflict variant.

    ``callable_status`` is set to a literal because ``ExplicitId`` selectors
    don't reference it; only ``NextReady`` selectors do.
    """
    loader = DataverseQueueLoader(client, translator, callable_status="ready")
    # Note: errors propagate. The `loaded is None` (row not found) case is
    # mapped to a CrmConflictError so the operator-visible discriminator
    # matches the initial-run conflict path — see docstring.
    loaded = loader.load_with_baseline(
        ExplicitId(queue_item_id), now_utc_ms=clk.now_utc_ms()
    )
    if loaded is None:
        raise CrmConflictError(queue_item_id, ["__row_deleted__"])
    _, baseline = loaded
    adapter.record_baseline(baseline)


__all__ = ("ResumeError", "ResumeReport", "resume_session")
