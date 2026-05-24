"""DataverseWriteBackAdapter — Slice 2 write-back path (FR-003, FR-015-FR-018, FR-024).

Implements the unchanged Slice 1 `WriteBackAdapter` protocol against the Dataverse
Web API. Per emit_* call the adapter:

1. Translates the conceptual `*Payload` to Dataverse logical-name fields via
   `MappingTranslator` — only `approved_update_field`-flagged fields are written;
   `preserve_if_present` and non-mapped fields are omitted (FR-003).
2. Pre-queries Dataverse for the idempotency-key match before any create — a hit is
   recorded as a confirmed correlation and the call returns without creating (FR-024).
3. POSTs (Phone Call activity, Task) or PATCHes (queue row) via `DataverseClient`,
   with bounded transient retry inherited from the client (FR-023).
4. Stamps `crm_correlations` and `writeback_progress` with the resulting state.

Vendor logical names and option-set integers never leave this module (SC-010).
See `specs/002-mock-call-real-crm/contracts/dataverse-adapter.md`.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterable
from datetime import UTC, datetime

from opencloser.crm.dataverse.client import DataverseClient
from opencloser.crm.dataverse.errors import (
    DataverseError,
    PermanentDataverseError,
    odata_guid_literal,
    odata_string_literal,
)
from opencloser.crm.dataverse.mapping import (
    MappingError,
    MappingTranslator,
)
from opencloser.models import (
    CrmCorrelation,
    CrmRecordKind,
    CrmWriteStatus,
    DataQualityWarning,
    Disposition,
    PhoneCallActivityPayload,
    QueueBaseline,
    QueueStatusUpdatePayload,
    RunStatus,
    TaskOwnersConfig,
    TaskPayload,
    WriteBack,
    WriteBackProgress,
)
from opencloser.state import store

# Belt-and-suspenders mirror of the Slice 1 FR-018 exclusion — emit_task no-ops for
# these dispositions even if the orchestrator misroutes the call.
_TASK_EXCLUDED_DISPOSITIONS: frozenset[Disposition] = frozenset(
    {
        Disposition.NOT_INTERESTED,
        Disposition.WRONG_NUMBER,
        Disposition.DO_NOT_CALL,
        Disposition.FAILED,
        Disposition.BLOCKED,
    }
)
_ODATA_FILTER = "$filter"
_ODATA_SELECT = "$select"
_ODATA_TOP = "$top"

# Conceptual mapping key for the queue's status field — referenced by
# `_check_conflict` to look up the Dataverse logical name and the baseline
# status value (T045).
_QUEUE_STATUS_FIELD = "queue.status"


class DataverseWriteBackError(RuntimeError):
    """A non-transient adapter-level failure (e.g. POST returned no OData-EntityId)."""


class CrmConflictError(DataverseWriteBackError):
    """T045 — a human-driven mid-run change was detected on the Dataverse queue
    row between the runner's baseline snapshot and the final queue-status PATCH.
    The adapter refuses the PATCH; the runner converts this into an
    operator-visible ``CrmRunReport(exit_status="blocked", message="conflict_detected: ...")``
    per spec §Edge Cases "Dataverse queue item changed by a human between claim
    and write-back".

    Subclassed from ``DataverseWriteBackError`` so the runner's existing
    ``except (DataverseError, DataverseWriteBackError, MappingError)`` block
    catches it; the runner then narrows on ``CrmConflictError`` first to map
    it to ``blocked`` (with `block_reason=conflict_detected`) rather than the
    default ``resume_needed``/``failed`` mapping. Treated as a permanent
    Dataverse error per spec §Definitions §Permanent Dataverse error — never
    retried, never escalated to ``resume_needed``.
    """

    def __init__(self, queue_item_id: str, conflicting_fields: list[str]) -> None:
        self.queue_item_id = queue_item_id
        self.conflicting_fields = list(conflicting_fields)
        joined = ", ".join(conflicting_fields) if conflicting_fields else "(unknown)"
        super().__init__(
            f"mid-run CRM-state conflict on queue item {queue_item_id!r}: "
            f"the following field(s) changed since load: {joined}. "
            "Write-back stopped before the final queue-status update; "
            "manual reconciliation required (T045)."
        )


class _AggregateBuilder:
    """One session's in-progress write-back parts, used by `build_writeback`."""

    __slots__ = ("phone_call_activity", "queue_status_update", "task")

    def __init__(self) -> None:
        self.phone_call_activity: PhoneCallActivityPayload | None = None
        self.queue_status_update: QueueStatusUpdatePayload | None = None
        self.task: TaskPayload | None = None


class _PendingFailure:
    """In-memory snapshot of one failure that `_record_failure` will persist
    once the orchestrator's rolling-back transaction has released its write
    lock — see `DataverseWriteBackAdapter.flush_pending_failures`."""

    __slots__ = ("dataverse_record_id", "error", "progress_key", "record_kind", "session_id")

    def __init__(
        self,
        *,
        session_id: str,
        record_kind: CrmRecordKind,
        error: Exception,
        progress_key: str,
        dataverse_record_id: str | None,
    ) -> None:
        self.session_id = session_id
        self.record_kind = record_kind
        self.error = error
        self.progress_key = progress_key
        self.dataverse_record_id = dataverse_record_id


class DataverseWriteBackAdapter:
    """Dataverse implementation of the Slice 1 `WriteBackAdapter` protocol."""

    def __init__(
        self,
        *,
        conn: sqlite3.Connection,
        client: DataverseClient,
        translator: MappingTranslator,
        task_owners: TaskOwnersConfig,
        now_utc_ms: Callable[[], str] | None = None,
        dry_run: bool = False,
    ) -> None:
        self._conn = conn
        self._client = client
        self._t = translator
        self._task_owners = task_owners
        self._now_utc_ms = now_utc_ms or _default_now_utc_ms
        # FR-031 dry-run: when True, every emit_* translates the payload via the
        # same mapping helpers as the write-enabled path, captures the planned
        # payload in `_aggregates`, and short-circuits BEFORE any GET / POST /
        # PATCH against `self._client`. `_record_correlation`, `_mark_progress`,
        # and `finalize_progress` are skipped — a dry-run leaves no
        # `crm_correlations` or `writeback_progress` row, because there is no
        # CRM correlation and no resumable state to record. Owner verification
        # is also skipped (it would require live Dataverse) — dry-run captures
        # the CONFIGURED default owner so the planned-payload artifact reflects
        # what a write-enabled run with a verified default would send (FR-025).
        self._dry_run = dry_run
        self._aggregates: dict[str, _AggregateBuilder] = {}
        # Operator-visible warnings (e.g. owner-override fallback per FR-025).
        self._warnings: list[DataQualityWarning] = []
        # `_record_failure` cannot write to the DB synchronously: the orchestrator
        # wraps every `crm.emit_*` in `with store.transaction(conn)`, and SQLite
        # allows only one writer at a time — a peer-connection write would
        # deadlock, and a same-connection write would be rolled back when the
        # emit re-raises. Instead, `_record_failure` stages the row in memory
        # here; the runner calls `flush_pending_failures` AFTER catching the
        # exception (when the orchestrator's transaction has rolled back and
        # the write lock is free).
        self._pending_failures: list[_PendingFailure] = []
        # T045 — the runner's claim-time snapshot, set via `record_baseline`
        # before the orchestrator drives the emit_* sequence. `None` means
        # "no baseline available; skip conflict detection" so dry-run and
        # tests that don't exercise the conflict path are unaffected.
        self._baseline: QueueBaseline | None = None

    # ----- public protocol surface -----------------------------------------

    def emit_phone_call_activity(self, payload: PhoneCallActivityPayload) -> None:
        entity_key = "phone_call_activity"
        idempotency_field = self._t.logical_name("phone_call.idempotency_key")
        if self._dry_run:
            # Validate every LOCAL mapping lookup the write-enabled path would
            # do — `_primary_id`, `_entity_set`, the body builder — so a
            # mapping gap (e.g. missing `entities['phone_call_activity']
            # .primary_id`) surfaces in dry-run instead of passing silently
            # only to fail immediately in write-enabled (Codex PR #7 review,
            # `contracts/metadata-discovery-verification.md` §5: dry-run
            # "still runs `verify` and surfaces gaps").
            self._entity_set(entity_key)
            self._primary_id(entity_key)
            self._phone_call_body(payload, idempotency_field)
            self._aggregate(payload.session_id).phone_call_activity = payload
            return
        try:
            record_id = self._idempotent_create(
                entity_key=entity_key,
                idempotency_field=idempotency_field,
                idempotency_value=payload.session_id,
                body=self._phone_call_body(payload, idempotency_field),
            )
        except (DataverseError, DataverseWriteBackError, MappingError) as exc:
            self._record_failure(
                session_id=payload.session_id,
                record_kind=CrmRecordKind.PHONE_CALL_ACTIVITY,
                error=exc,
                progress_key="phone_call_activity_done",
            )
            raise
        self._record_correlation(
            session_id=payload.session_id,
            record_kind=CrmRecordKind.PHONE_CALL_ACTIVITY,
            idempotency_key=payload.session_id,
            dataverse_record_id=record_id,
        )
        self._mark_progress(payload.session_id, phone_call_activity_done=True)
        self._aggregate(payload.session_id).phone_call_activity = payload

    def emit_queue_status_update(self, payload: QueueStatusUpdatePayload) -> None:
        # PATCH is keyed by the queue row's primary id directly; the FR-024 idempotency
        # signal lives in the `last_session_id` column rather than a synthetic key
        # column. A row whose `last_session_id` already equals this session has been
        # patched in a prior run — record/refresh the correlation and skip the PATCH.
        # Mapping resolution + the idempotency pre-query + the PATCH all run inside
        # the same failure-recording try/except so any Dataverse access error in
        # this path persists a consistent `crm_correlations(write_status=failed)`
        # row before re-raising.
        if self._dry_run:
            # Validate every LOCAL mapping lookup the write-enabled path would
            # do — `_entity_set`, `_primary_id`, the body builder (Codex PR #7
            # round-3 review: `_fetch_queue_last_session` calls
            # `_primary_id("queue_item")` in the write-enabled path, so a
            # mapping missing `entities['queue_item'].primary_id` MUST surface
            # in dry-run too). Skip the GET pre-query and the PATCH; capture
            # the conceptual payload (FR-031, FR-010 — dry-run MUST NOT
            # mutate the CRM queue item).
            self._entity_set("queue_item")
            self._primary_id("queue_item")
            self._queue_status_body(payload)
            self._aggregate(payload.session_id).queue_status_update = payload
            return
        try:
            entity_set = self._entity_set("queue_item")
            existing = self._fetch_queue_last_session(payload.queue_item_id)
            if existing == payload.session_id:
                self._record_correlation(
                    session_id=payload.session_id,
                    record_kind=CrmRecordKind.QUEUE_STATUS,
                    idempotency_key=payload.session_id,
                    dataverse_record_id=payload.queue_item_id,
                )
                self._mark_progress(payload.session_id, queue_status_update_done=True)
                self._aggregate(payload.session_id).queue_status_update = payload
                return

            # T045 — mid-run conflict detection. Fresh GET of the queue row;
            # compare against the runner's claim-time baseline. A mismatch
            # raises `CrmConflictError` (a `DataverseWriteBackError` subclass)
            # so the runner's existing failure-recording try/except records a
            # `crm_correlations(write_status=failed)` row + stamps
            # `writeback_progress(run_status=blocked)`. The runner narrows on
            # `CrmConflictError` to surface `exit_status="blocked",
            # block_reason="conflict_detected"` rather than the default
            # `resume_needed`/`failed` mapping.
            self._check_conflict(payload.queue_item_id)

            body = self._queue_status_body(payload)
            path = f"{entity_set}({payload.queue_item_id})"
            # Pass 1B (2026-05-24 audit-remediation): close the TOCTOU window
            # between `_check_conflict`'s GET and this PATCH using Dataverse's
            # optimistic-concurrency `If-Match` header. The baseline captures
            # the row's `@odata.etag` at load time; a human edit landing
            # between conflict-check and PATCH bumps the etag and Dataverse
            # returns 412 Precondition Failed. We map 412 → `CrmConflictError`
            # so the runner surfaces `exit_status="blocked"` consistently
            # with the conflict-check path. When `etag` is None (the loader
            # didn't capture one — typical in tests that don't seed it),
            # PATCH proceeds unconditionally.
            headers: dict[str, str] = {}
            if self._baseline is not None and self._baseline.etag is not None:
                headers["If-Match"] = self._baseline.etag
            try:
                self._client.patch(path, json=body, headers=headers or None)
            except PermanentDataverseError as exc:
                if exc.status_code == 412:
                    raise CrmConflictError(
                        payload.queue_item_id, ["@odata.etag"]
                    ) from exc
                raise
        except (DataverseError, DataverseWriteBackError, MappingError) as exc:
            # `DataverseWriteBackError` here is the T045 `CrmConflictError`
            # path — record the failed correlation + stamp the progress row
            # so resume sees the conflict-blocked state. The runner narrows
            # on `CrmConflictError` (subclass) to surface `exit_status=blocked`.
            self._record_failure(
                session_id=payload.session_id,
                record_kind=CrmRecordKind.QUEUE_STATUS,
                error=exc,
                progress_key="queue_status_update_done",
                dataverse_record_id=payload.queue_item_id,
            )
            raise
        self._record_correlation(
            session_id=payload.session_id,
            record_kind=CrmRecordKind.QUEUE_STATUS,
            idempotency_key=payload.session_id,
            dataverse_record_id=payload.queue_item_id,
        )
        self._mark_progress(payload.session_id, queue_status_update_done=True)
        self._aggregate(payload.session_id).queue_status_update = payload

    def emit_task(self, payload: TaskPayload) -> None:
        # FR-018 belt-and-suspenders — runs entirely before any Dataverse access.
        session = store.get_session(self._conn, payload.session_id)
        if session is None or session.final_disposition is None:
            return
        if session.final_disposition in _TASK_EXCLUDED_DISPOSITIONS:
            return

        entity_key = "task"
        idempotency_field = self._t.logical_name("task.idempotency_key")

        if self._dry_run:
            # Validate every LOCAL mapping lookup the write-enabled path would
            # do — `_primary_id`, `_entity_set`, the body builder — so missing
            # `entities['task'].primary_id` surfaces in dry-run (Codex PR #7
            # review). Owner override + verification (`_resolve_task_owner`)
            # are deliberately skipped: both require live Dataverse GETs
            # (`_lookup_owner_override`, `_owner_entity_set`), which the
            # spec §Edge Cases path explicitly tolerates being unreachable in
            # dry-run. We use the configured default owner directly and
            # default the entity-set to "systemusers" (the common case). A
            # write-enabled run still re-verifies the owner against
            # active-enabled rows (FR-025).
            self._entity_set(entity_key)
            self._primary_id(entity_key)
            default_owner = (
                self._task_owners.callback
                if payload.task_kind == "callback"
                else self._task_owners.review
            )
            self._task_body(
                payload,
                idempotency_field=idempotency_field,
                owner_id=default_owner,
                owner_entity_set="systemusers",
            )
            stamped = payload.model_copy(update={"assigned_to": default_owner})
            self._aggregate(payload.session_id).task = stamped
            return

        # Owner-resolution + body construction + the POST all run inside the same
        # try/except so a Dataverse failure ANYWHERE in the emit_task path (override
        # lookup, owner verification, or the create itself) records a
        # `crm_correlations(write_status=failed)` row and stamps
        # `writeback_progress(run_status=blocked)` before re-raising — keeping the
        # audit/resume ledger consistent. `MappingError` (from `_primary_id`) and
        # transient `DataverseError` are caught too: the runner normalizes both
        # into operator-visible `exit_status=failed` reports.
        try:
            resolved = self._resolve_task_owner(payload)
            if resolved is None:
                # FR-025 unverifiable-default-owner branch — `_resolve_task_owner`
                # has already recorded an operator-visible warning. We raise
                # `DataverseWriteBackError` so the outer try/except records a
                # failed correlation + blocks the run (the disposition asked
                # for a Task and we cannot create one without a valid owner —
                # silently returning would let the run report `completed`
                # while the required human follow-up went unwritten).
                raise DataverseWriteBackError(
                    f"task emission blocked for session {payload.session_id!r}: "
                    "no verifiable default or override owner (FR-025)"
                )
            owner_id, owner_entity_set = resolved
            body = self._task_body(
                payload,
                idempotency_field=idempotency_field,
                owner_id=owner_id,
                owner_entity_set=owner_entity_set,
            )
            record_id = self._idempotent_create(
                entity_key=entity_key,
                idempotency_field=idempotency_field,
                idempotency_value=payload.session_id,
                body=body,
            )
        except (DataverseError, DataverseWriteBackError, MappingError) as exc:
            self._record_failure(
                session_id=payload.session_id,
                record_kind=CrmRecordKind.TASK,
                error=exc,
                progress_key="task_done",
            )
            raise
        self._record_correlation(
            session_id=payload.session_id,
            record_kind=CrmRecordKind.TASK,
            idempotency_key=payload.session_id,
            dataverse_record_id=record_id,
        )
        self._mark_progress(payload.session_id, task_done=True)
        stamped = payload.model_copy(update={"assigned_to": owner_id})
        self._aggregate(payload.session_id).task = stamped

    def build_writeback(self, session_id: str) -> WriteBack:
        agg = self._aggregates.get(session_id)
        if agg is None or agg.queue_status_update is None:
            raise KeyError(f"No queue-status update emitted for session {session_id!r} yet")
        return WriteBack(
            session_id=session_id,
            phone_call_activity=agg.phone_call_activity,
            queue_status_update=agg.queue_status_update,
            task=agg.task,
        )

    # ----- public observability --------------------------------------------

    def pending_failure_session_ids(self) -> list[str]:
        """Session IDs in the in-memory pending-failure queue. Used by the
        runner to surface a `session_id` on `RESUME_NEEDED` reports — the
        orchestrator's caught exception doesn't carry it, but the adapter
        staged it in `_record_failure` before the orchestrator's transaction
        rolled back (Copilot PR #9 round-2 P1: operators need this id to
        invoke `run-crm --resume <session-id>`)."""
        seen: list[str] = []
        for failure in self._pending_failures:
            if failure.session_id not in seen:
                seen.append(failure.session_id)
        return seen

    def record_baseline(self, baseline: QueueBaseline) -> None:
        """T045 — register the runner's claim-time snapshot of the Dataverse
        queue row. ``emit_queue_status_update`` consults it via
        ``_check_conflict`` before issuing the final PATCH; a mismatch raises
        ``CrmConflictError`` and the runner converts that into an
        operator-visible ``blocked`` exit. No-op in dry-run (the adapter never
        PATCHes in dry-run, so there's nothing to gate)."""
        self._baseline = baseline

    def warnings(self) -> list[DataQualityWarning]:
        """Operator-visible warnings accumulated during this adapter's session
        (e.g. an owner-override fallback per FR-025)."""
        return list(self._warnings)

    def add_warning(self, warning: DataQualityWarning) -> None:
        """Record an operator-visible warning (e.g. FR-034 non-E.164 phone)."""
        self._warnings.append(warning)

    def finalize_progress(self, session_id: str, *, run_status: RunStatus) -> None:
        """Stamp the per-session resume ledger's terminal status (FR-023). Called
        by the runner once every emit_* for this session has completed (or been
        skipped).

        In dry-run mode this is a no-op: no Dataverse write was issued, so there
        is no CRM write-back to resume and no `writeback_progress` row to stamp.
        """
        if self._dry_run:
            return
        progress = self._load_progress(session_id) or self._new_progress(session_id)
        if (
            progress.phone_call_activity_done
            or progress.queue_status_update_done
            or progress.task_done
        ) or run_status is not RunStatus.IN_PROGRESS:
            store.upsert_writeback_progress(
                self._conn,
                WriteBackProgress(
                    session_id=session_id,
                    phone_call_activity_done=progress.phone_call_activity_done,
                    queue_status_update_done=progress.queue_status_update_done,
                    task_done=progress.task_done,
                    run_status=run_status,
                    last_error=progress.last_error
                    if run_status is not RunStatus.COMPLETED
                    else None,
                    updated_at=self._now_utc_ms(),
                ),
            )

    # ----- payload translation ---------------------------------------------

    def _phone_call_body(
        self, payload: PhoneCallActivityPayload, idempotency_field: str
    ) -> dict[str, object]:
        return {
            "subject": (payload.summary or f"Mock call — {payload.final_disposition.value}")[:200],
            "description": payload.summary,
            "actualstart": payload.started_at,
            "actualend": payload.ended_at,
            idempotency_field: payload.session_id,
        }

    def _queue_status_body(self, payload: QueueStatusUpdatePayload) -> dict[str, object]:
        approved = self._t.approved_update_logical_names()
        candidates: dict[str, object] = {
            self._t.logical_name("queue.status"): self._t.option_set_value(
                f"queue_status.{payload.new_status.value}"
            ),
            self._t.logical_name("queue.last_disposition"): payload.transition_reason,
            self._t.logical_name("queue.last_session_id"): payload.session_id,
        }
        # `queue.last_error` carries either a block reason or, when only data-quality
        # warnings exist (e.g. FR-034 non-E.164 phone), the warning summary. This keeps
        # warnings visible on the Dataverse queue row without changing the disposition.
        last_error = self._compose_last_error(payload)
        if last_error is not None:
            candidates[self._t.logical_name("queue.last_error")] = last_error
        # DNC flag is set only when the transition is to dnc.
        if payload.new_status.value == "dnc":
            candidates[self._t.logical_name("queue.dnc")] = True
        # FR-003 — drop any field whose mapping isn't `approved_update_field`.
        return {field: value for field, value in candidates.items() if field in approved}

    def _compose_last_error(self, payload: QueueStatusUpdatePayload) -> str | None:
        warning_summary = "; ".join(f"{w.code}:{w.message}" for w in self._warnings)
        if payload.transition_reason.startswith("blocked_by_"):
            return (
                f"{payload.transition_reason} ({warning_summary})"
                if warning_summary
                else payload.transition_reason
            )
        return warning_summary or None

    def _task_body(
        self,
        payload: TaskPayload,
        *,
        idempotency_field: str,
        owner_id: str,
        owner_entity_set: str,
    ) -> dict[str, object]:
        # `preferred_callback_window` is intentionally free-form text (e.g.
        # "Thursday afternoon") per the Slice 1 contract; it MUST NOT be written to
        # the Dataverse `scheduledend` column (an Edm.DateTimeOffset that 400s on
        # non-ISO input). The window is surfaced in `description` instead.
        subject = payload.subject[:200] if payload.subject else "Follow-up"
        return {
            "subject": subject,
            "description": _task_description(payload),
            idempotency_field: payload.session_id,
            "ownerid@odata.bind": _owner_bind(owner_id, owner_entity_set),
        }

    # ----- Dataverse interaction helpers -----------------------------------

    def _idempotent_create(
        self,
        *,
        entity_key: str,
        idempotency_field: str,
        idempotency_value: str,
        body: dict[str, object],
    ) -> str:
        """FR-024 — pre-query for an existing record with this idempotency key; if
        found, return its id. Otherwise POST and return the new record id.

        A POST that succeeds but omits an `OData-EntityId` response header is a
        permanent adapter-level failure: we cannot record a confirmed correlation
        without the new record's id, and silently storing an empty id would mask
        the failure on every later resume/audit.
        """
        entity_set = self._entity_set(entity_key)
        primary_id = self._primary_id(entity_key)
        existing = (
            self._client.get(
                entity_set,
                params={
                    _ODATA_FILTER: (
                        f"{idempotency_field} eq {odata_string_literal(idempotency_value)}"
                    ),
                    _ODATA_SELECT: primary_id,
                    _ODATA_TOP: "1",
                },
            )
            .json()
            .get("value", [])
        )
        if existing:
            existing_id = existing[0].get(primary_id)
            if not existing_id:
                raise DataverseWriteBackError(
                    f"idempotency pre-query for {entity_set} returned a row without "
                    f"its primary id {primary_id!r}"
                )
            return str(existing_id)
        response = self._client.post(entity_set, json=body)
        entity_uri = response.headers.get("OData-EntityId", "")
        record_id = _parse_record_id_from_uri(entity_uri)
        if not record_id:
            raise DataverseWriteBackError(
                f"POST {entity_set} succeeded but response carried no OData-EntityId "
                f"header — cannot record a confirmed correlation"
            )
        return record_id

    def _fetch_queue_last_session(self, queue_item_id: str) -> str | None:
        entity_set = self._entity_set("queue_item")
        primary_id = self._primary_id("queue_item")
        last_session_field = self._t.logical_name("queue.last_session_id")
        rows = (
            self._client.get(
                entity_set,
                params={
                    _ODATA_FILTER: f"{primary_id} eq {odata_guid_literal(queue_item_id)}",
                    _ODATA_SELECT: last_session_field,
                    _ODATA_TOP: "1",
                },
            )
            .json()
            .get("value", [])
        )
        if not rows:
            return None
        value = rows[0].get(last_session_field)
        return None if value is None else str(value)

    def _check_conflict(self, queue_item_id: str) -> None:
        """T045 — fresh GET of the queue row immediately before the final PATCH;
        raise ``CrmConflictError`` if any baseline value has changed.

        Compared fields (Pass 1B, 2026-05-24 audit-remediation):
          * ``queue.status`` — option-set value at load. Raw comparison
            (no coercion) so a `None`-at-load round-trips correctly.
          * ``queue.last_session_id`` — captures concurrent-session clobbers
            (a different session — or a human — wrote this field between
            our load and our PATCH). Critical for ExplicitId selectors,
            which the FR-009 callable-status filter doesn't protect.
          * ``preserve_if_present`` mapped logical names — any value change
            means a human edited a high-confidence field during our run.

        Row-deletion semantics: when the fresh GET returns no rows, the row
        was deleted between load and final write. Per spec §Edge Cases
        ("Dataverse queue item changed by a human between claim and
        write-back"), this IS a human change, not a generic Dataverse
        failure — raise ``CrmConflictError(["__row_deleted__"])`` so the
        runner surfaces ``exit_status="blocked", block_reason="conflict_detected"``.

        A ``None`` baseline (no ``record_baseline`` call by the runner) skips
        the check — preserves backward compatibility for callers that don't
        opt in (the existing US1/US4 happy-path tests construct the adapter
        directly without a baseline). The check also no-ops when the
        baseline is for a different queue item id (defensive — never compare
        across queue items).
        """
        baseline = self._baseline
        if baseline is None or baseline.queue_item_id != queue_item_id:
            return

        status_field = self._t.logical_name(_QUEUE_STATUS_FIELD)
        last_session_field = self._t.logical_name("queue.last_session_id")
        preserve_fields = self._t.preserve_if_present()
        select_fields = sorted({status_field, last_session_field, *preserve_fields})

        entity_set = self._entity_set("queue_item")
        primary_id = self._primary_id("queue_item")
        rows = (
            self._client.get(
                entity_set,
                params={
                    _ODATA_FILTER: f"{primary_id} eq {odata_guid_literal(queue_item_id)}",
                    _ODATA_SELECT: ",".join(select_fields),
                    _ODATA_TOP: "1",
                },
            )
            .json()
            .get("value", [])
        )
        if not rows:
            # Row deleted between load and final PATCH. Spec §Edge Cases
            # classifies any human-change-mid-run as a conflict; raise rather
            # than letting the subsequent PATCH 404 into a generic `failed`.
            raise CrmConflictError(queue_item_id, ["__row_deleted__"])

        current = rows[0]
        conflicting: list[str] = []
        # Status change → conflict. Raw comparison (no coercion).
        if current.get(status_field) != baseline.status_value:
            conflicting.append(status_field)
        # last_session_id change → concurrent-session clobber. Normalize to
        # string-or-None on both sides so a stringified GUID compares cleanly.
        current_last_session = current.get(last_session_field)
        current_last_session = (
            None if current_last_session is None else str(current_last_session)
        )
        if current_last_session != baseline.last_session_id:
            conflicting.append(last_session_field)
        # Preserve_if_present change → human edit during our run. Missing-on-
        # current is treated as `None`; baseline holds `None` for fields that
        # weren't set at load, so an explicit add-by-human (None → non-None)
        # is caught the same as a value-change.
        for field in preserve_fields:
            if current.get(field) != baseline.preserve_values.get(field):
                conflicting.append(field)

        if conflicting:
            raise CrmConflictError(queue_item_id, conflicting)

    def _entity_set(self, entity_key: str) -> str:
        """Resolve the Dataverse Web API entity-set (collection) name for an entity
        key. Thin wrapper around `MappingTranslator.entity_set_name` so the
        adapter's call sites read naturally."""
        return self._t.entity_set_name(entity_key)

    def _primary_id(self, entity_key: str) -> str:
        """Return the mapped primary-id column for an entity. Raises `MappingError`
        when the mapping omits it — Dataverse activity tables use `activityid`
        (not `<logical>id`), so a silent fallback would generate broken $select
        clauses for `phone_call_activity` / `task` (FR-001/FR-004)."""
        ref = self._t.entity(entity_key)
        if not ref.primary_id:
            raise MappingError(
                f"mapping artifact is missing entities[{entity_key!r}].primary_id — "
                "Dataverse activity tables use 'activityid', not '<logical>id', and "
                "the adapter refuses to guess. Set primary_id in dataverse_mapping.json."
            )
        return ref.primary_id

    def _record_failure(
        self,
        *,
        session_id: str,
        record_kind: CrmRecordKind,
        error: Exception,
        progress_key: str,
        dataverse_record_id: str | None = None,
    ) -> None:
        """Stage a failure marker in memory; the runner persists it via
        `flush_pending_failures` after the orchestrator's transaction rolls back.

        We CANNOT write here: the orchestrator wraps every `crm.emit_*` in
        `with store.transaction(conn)`, and SQLite is single-writer — a peer
        connection would deadlock waiting for the open write lock, and a
        same-connection write would be rolled back when the caller re-raises.
        Deferring the writes until after the rollback releases the lock is the
        only correctness-preserving option.
        """
        self._pending_failures.append(
            _PendingFailure(
                session_id=session_id,
                record_kind=record_kind,
                error=error,
                progress_key=progress_key,
                dataverse_record_id=dataverse_record_id,
            )
        )

    def flush_pending_failures(
        self, *, failure_run_status: RunStatus = RunStatus.BLOCKED
    ) -> None:
        """Persist every staged failure to `crm_correlations` + `writeback_progress`.

        The runner calls this after catching the emit_* exception — at that
        point the orchestrator's `with store.transaction(conn)` has rolled back
        and released the SQLite write lock, so a normal write on the shared
        connection succeeds and the failure markers persist.

        ``failure_run_status`` controls the terminal state stamped on
        ``writeback_progress`` for this batch (default ``BLOCKED`` —
        the conservative permanent-error case). The runner passes
        ``RESUME_NEEDED`` when the underlying failure is a
        ``TransientDataverseError`` (retry budget exhausted), so the resume
        coordinator can later replay the missing emits (FR-023 + Copilot
        PR #9 review: previously ``RESUME_NEEDED`` was never set anywhere,
        so the resume coordinator could not be triggered by real failed
        runs).

        Each upsert preserves:
        - A prior `CONFIRMED` correlation rather than downgrading it (a later
          transient failure on an already-confirmed record must not undo
          audit truth).
        - A prior `*_done=True` flag (regressing it would mislead the resume
          coordinator into replaying a write that already succeeded).
        - A terminal `COMPLETED` run_status (a later transient failure on an
          already-completed session must not regress the ledger to BLOCKED
          or RESUME_NEEDED).
        """
        if not self._pending_failures:
            return
        for failure in self._pending_failures:
            self._persist_failure(failure, failure_run_status=failure_run_status)
        self._pending_failures.clear()

    def _persist_failure(
        self, failure: _PendingFailure, *, failure_run_status: RunStatus
    ) -> None:
        now = self._now_utc_ms()
        existing = store.get_crm_correlation(
            self._conn, failure.session_id, failure.record_kind
        )
        previously_confirmed = (
            existing is not None and existing.write_status is CrmWriteStatus.CONFIRMED
        )
        correlation = CrmCorrelation(
            session_id=failure.session_id,
            record_kind=failure.record_kind,
            idempotency_key=failure.session_id,
            dataverse_record_id=(
                existing.dataverse_record_id
                if previously_confirmed
                else failure.dataverse_record_id
            ),
            write_status=(
                CrmWriteStatus.CONFIRMED if previously_confirmed else CrmWriteStatus.FAILED
            ),
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        progress = self._load_progress(failure.session_id)
        already_done = bool(progress and getattr(progress, failure.progress_key))
        next_run_status = (
            RunStatus.COMPLETED
            if progress is not None and progress.run_status is RunStatus.COMPLETED
            else failure_run_status
        )
        store.upsert_crm_correlation(self._conn, correlation)
        progress_update = {} if already_done else {failure.progress_key: False}
        self._mark_progress(
            failure.session_id,
            last_error=str(failure.error),
            run_status=next_run_status,
            **progress_update,
        )

    # ----- ownership resolution (FR-025) -----------------------------------

    def _resolve_task_owner(self, payload: TaskPayload) -> tuple[str, str] | None:
        """Spec §Definitions §Approved owner override — return `(owner_id, entity_set)`
        where `entity_set` is `"systemusers"` or `"teams"` so the @odata.bind targets
        the right entity set. Returns `None` when neither the override nor the default
        can be verified as an active enabled Dataverse user/team (FR-025 — never write
        an unverified owner id).

        Resolution order:
        1. The override id carried on the queue row's mapped override field, if and
           only if it resolves to an **active enabled** systemuser/team.
        2. The configured default owner for the Task kind, again only when it
           resolves to an active enabled systemuser/team.

        An override that fails verification produces an operator-visible warning and
        falls back to the default; a default that also fails verification produces a
        second warning and the Task emission is skipped by the caller.
        """
        default = (
            self._task_owners.callback
            if payload.task_kind == "callback"
            else self._task_owners.review
        )
        override = self._lookup_owner_override(payload.queue_item_id)
        if override is not None:
            entity_set = self._owner_entity_set(override)
            if entity_set is not None:
                return override, entity_set
            self._warnings.append(
                DataQualityWarning(
                    code="task_owner_override_unverifiable",
                    field="task_owner_override",
                    message=(
                        f"override owner {override!r} for queue item "
                        f"{payload.queue_item_id!r} is not an active Dataverse user or "
                        f"team — falling back to default"
                    ),
                )
            )
        default_entity_set = self._owner_entity_set(default)
        if default_entity_set is not None:
            return default, default_entity_set
        # FR-025 — the configured default itself is unverifiable. Task write-back is
        # blocked rather than writing an unverified id.
        self._warnings.append(
            DataQualityWarning(
                code="task_owner_default_unverifiable",
                field="task_owner_default",
                message=(
                    f"configured default task owner {default!r} for task_kind="
                    f"{payload.task_kind!r} is not an active Dataverse user or team "
                    f"— task emission blocked"
                ),
            )
        )
        return None

    def _lookup_owner_override(self, queue_item_id: str) -> str | None:
        override_field = self._t.mapping.task_owner_override_field
        if not override_field:
            return None
        entity_set = self._entity_set("queue_item")
        primary_id = self._primary_id("queue_item")
        rows = (
            self._client.get(
                entity_set,
                params={
                    _ODATA_FILTER: f"{primary_id} eq {odata_guid_literal(queue_item_id)}",
                    _ODATA_SELECT: override_field,
                    _ODATA_TOP: "1",
                },
            )
            .json()
            .get("value", [])
        )
        if not rows:
            return None
        value = rows[0].get(override_field)
        if value in (None, ""):
            return None
        return str(value)

    def _owner_entity_set(self, owner_id: str) -> str | None:
        """Return the Dataverse entity-set name (`"systemusers"` or `"teams"`) for an
        active enabled owner id, or `None` when no active enabled record matches.

        Active-enabled gate per spec §Definitions §Approved owner override:
        - `systemuser`: row must exist AND `isdisabled == false`.
        - `team`: row must exist (teams have no `isdisabled` column).

        404 on the systemuser path (the table genuinely doesn't carry this id)
        is treated as "not found here, try teams next". Every OTHER permanent
        Dataverse error — 401/403 from a permission regression, 400 from a
        malformed query — is allowed to propagate so emit_task's outer
        try/except records a failed task correlation rather than silently
        degrading the run to "owner unverifiable → fallback".
        """
        for entity_set, primary_id, extra_filter in (
            ("systemusers", "systemuserid", " and isdisabled eq false"),
            ("teams", "teamid", ""),
        ):
            try:
                rows = (
                    self._client.get(
                        entity_set,
                        params={
                            _ODATA_FILTER: f"{primary_id} eq {odata_guid_literal(owner_id)}{extra_filter}",
                            _ODATA_SELECT: primary_id,
                            _ODATA_TOP: "1",
                        },
                    )
                    .json()
                    .get("value", [])
                )
            except PermanentDataverseError as exc:
                # Only HTTP 404 (table truly absent in this environment) is
                # benign — try the next entity set. Anything else (401/403
                # permission regression, 400 malformed query) is real and must
                # surface, so emit_task can record a failed task correlation.
                if exc.status_code == 404:
                    continue
                raise
            if rows:
                return entity_set
        return None

    # ----- correlation + progress ledger -----------------------------------

    def _aggregate(self, session_id: str) -> _AggregateBuilder:
        agg = self._aggregates.get(session_id)
        if agg is None:
            agg = _AggregateBuilder()
            self._aggregates[session_id] = agg
        return agg

    def _record_correlation(
        self,
        *,
        session_id: str,
        record_kind: CrmRecordKind,
        idempotency_key: str,
        dataverse_record_id: str | None,
    ) -> None:
        now = self._now_utc_ms()
        existing = store.get_crm_correlation(self._conn, session_id, record_kind)
        store.upsert_crm_correlation(
            self._conn,
            CrmCorrelation(
                session_id=session_id,
                record_kind=record_kind,
                idempotency_key=idempotency_key,
                dataverse_record_id=dataverse_record_id,
                write_status=CrmWriteStatus.CONFIRMED,
                created_at=existing.created_at if existing else now,
                updated_at=now,
            ),
        )

    def _mark_progress(
        self,
        session_id: str,
        *,
        phone_call_activity_done: bool | None = None,
        queue_status_update_done: bool | None = None,
        task_done: bool | None = None,
        last_error: str | None = None,
        run_status: RunStatus | None = None,
    ) -> None:
        """Upsert the per-session resume ledger. `None` for any kwarg means
        "leave the existing value alone".

        `run_status` defaults to `None` (preserve existing) rather than
        `IN_PROGRESS` so a per-emit `*_done` flip cannot regress an already-
        terminal `COMPLETED`/`BLOCKED` row back to `IN_PROGRESS`. The first call
        for a brand-new session falls back to `IN_PROGRESS` via
        `_new_progress`; later callers either omit the kwarg (preserving
        whatever is there) or pass an explicit terminal value.
        """
        progress = self._load_progress(session_id) or self._new_progress(session_id)
        store.upsert_writeback_progress(
            self._conn,
            WriteBackProgress(
                session_id=session_id,
                phone_call_activity_done=(
                    progress.phone_call_activity_done
                    if phone_call_activity_done is None
                    else phone_call_activity_done
                ),
                queue_status_update_done=(
                    progress.queue_status_update_done
                    if queue_status_update_done is None
                    else queue_status_update_done
                ),
                task_done=progress.task_done if task_done is None else task_done,
                run_status=progress.run_status if run_status is None else run_status,
                last_error=last_error if last_error is not None else progress.last_error,
                updated_at=self._now_utc_ms(),
            ),
        )

    def _load_progress(self, session_id: str) -> WriteBackProgress | None:
        return store.get_writeback_progress(self._conn, session_id)

    def _new_progress(self, session_id: str) -> WriteBackProgress:
        return WriteBackProgress(
            session_id=session_id,
            phone_call_activity_done=False,
            queue_status_update_done=False,
            task_done=False,
            run_status=RunStatus.IN_PROGRESS,
            last_error=None,
            updated_at=self._now_utc_ms(),
        )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _parse_record_id_from_uri(entity_uri: str) -> str:
    """Extract the GUID from a Dataverse `OData-EntityId` URI of the form
    `<base>/<entity>(<guid>)`. Returns an empty string if the URI is malformed."""
    if not entity_uri:
        return ""
    lparen = entity_uri.rfind("(")
    rparen = entity_uri.rfind(")")
    if lparen < 0 or rparen < lparen:
        return ""
    return entity_uri[lparen + 1 : rparen].strip("'")


def _owner_bind(owner_id: str, entity_set: str) -> str:
    """OData @odata.bind value for an owner reference.

    `entity_set` is `"systemusers"` or `"teams"` — the Dataverse entity-set name
    matching where the owner was verified. Binding to the wrong set produces an
    HTTP 400 from real Dataverse (a team id under /systemusers does not resolve).
    """
    return f"/{entity_set}({owner_id})"


def _task_description(payload: TaskPayload) -> str:
    parts: list[str] = []
    if payload.task_kind == "callback":
        if payload.preferred_callback_window:
            parts.append(f"Callback window: {payload.preferred_callback_window}")
        if payload.captured_email:
            parts.append(f"Email: {payload.captured_email}")
    elif payload.task_kind == "review" and payload.reason_code is not None:
        parts.append(f"Review reason: {payload.reason_code.value}")
    return "\n".join(parts) if parts else payload.subject


def _default_now_utc_ms() -> str:
    """ISO 8601 / UTC / millisecond timestamp matching `core.clock.SystemClock`.

    Duplicated here rather than imported from `opencloser.core.clock` to keep the
    crm boundary's dependency direction clean (see tests/test_imports.py — the
    crm group's allowed-import set forbids `opencloser.core`).
    """
    now = datetime.now(UTC)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


__all__: Iterable[str] = (
    "CrmConflictError",
    "DataverseWriteBackAdapter",
    "DataverseWriteBackError",
    "MappingError",
)
