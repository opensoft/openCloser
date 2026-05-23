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
from opencloser.crm.dataverse.errors import PermanentDataverseError
from opencloser.crm.dataverse.mapping import MappingError, MappingTranslator
from opencloser.models import (
    CrmCorrelation,
    CrmRecordKind,
    CrmWriteStatus,
    DataQualityWarning,
    Disposition,
    PhoneCallActivityPayload,
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


class DataverseWriteBackError(RuntimeError):
    """A non-transient adapter-level failure (e.g. PATCH targeted a missing row)."""


class _AggregateBuilder:
    """One session's in-progress write-back parts, used by `build_writeback`."""

    __slots__ = ("phone_call_activity", "queue_status_update", "task")

    def __init__(self) -> None:
        self.phone_call_activity: PhoneCallActivityPayload | None = None
        self.queue_status_update: QueueStatusUpdatePayload | None = None
        self.task: TaskPayload | None = None


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
    ) -> None:
        self._conn = conn
        self._client = client
        self._t = translator
        self._task_owners = task_owners
        self._now_utc_ms = now_utc_ms or _default_now_utc_ms
        self._aggregates: dict[str, _AggregateBuilder] = {}
        # Operator-visible warnings (e.g. owner-override fallback per FR-025).
        self._warnings: list[DataQualityWarning] = []

    # ----- public protocol surface -----------------------------------------

    def emit_phone_call_activity(self, payload: PhoneCallActivityPayload) -> None:
        entity = self._t.entity_logical_name("phone_call_activity")
        idempotency_field = self._t.logical_name("phone_call.idempotency_key")
        record_id = self._idempotent_create(
            entity=entity,
            idempotency_field=idempotency_field,
            idempotency_value=payload.session_id,
            body=self._phone_call_body(payload, idempotency_field),
        )
        self._record_correlation(
            session_id=payload.session_id,
            record_kind=CrmRecordKind.PHONE_CALL_ACTIVITY,
            idempotency_key=payload.session_id,
            dataverse_record_id=record_id,
        )
        self._mark_progress(payload.session_id, phone_call_activity_done=True)
        self._aggregate(payload.session_id).phone_call_activity = payload

    def emit_queue_status_update(self, payload: QueueStatusUpdatePayload) -> None:
        entity = self._t.entity_logical_name("queue_item")
        # PATCH is keyed by the queue row's primary id directly; the FR-024 idempotency
        # signal lives in the `last_session_id` column rather than a synthetic key
        # column. A row whose `last_session_id` already equals this session has been
        # patched in a prior run — record/refresh the correlation and skip the PATCH.
        existing = self._fetch_queue_last_session(entity, payload.queue_item_id)
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

        body = self._queue_status_body(payload)
        path = f"{entity}({payload.queue_item_id})"
        try:
            self._client.patch(path, json=body)
        except PermanentDataverseError as exc:
            self._mark_progress(
                payload.session_id,
                queue_status_update_done=False,
                last_error=str(exc),
                run_status=RunStatus.BLOCKED,
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
        # FR-018 belt-and-suspenders.
        session = store.get_session(self._conn, payload.session_id)
        if session is None or session.final_disposition is None:
            return
        if session.final_disposition in _TASK_EXCLUDED_DISPOSITIONS:
            return

        entity = self._t.entity_logical_name("task")
        idempotency_field = self._t.logical_name("task.idempotency_key")

        # Resolve ownership BEFORE constructing the payload so the resolved owner is
        # stamped on TaskPayload.assigned_to too (Slice 1 left it null; data-model §5
        # makes it the Slice 2 wiring point). FR-025: an unverifiable default blocks
        # the Task emission rather than writing an unverified owner id.
        resolved = self._resolve_task_owner(payload)
        if resolved is None:
            return
        owner_id, owner_entity_set = resolved
        body = self._task_body(
            payload,
            idempotency_field=idempotency_field,
            owner_id=owner_id,
            owner_entity_set=owner_entity_set,
        )

        record_id = self._idempotent_create(
            entity=entity,
            idempotency_field=idempotency_field,
            idempotency_value=payload.session_id,
            body=body,
        )
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
        skipped)."""
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
        subject = payload.subject[:200] if payload.subject else "Follow-up"
        body: dict[str, object] = {
            "subject": subject,
            "description": _task_description(payload),
            idempotency_field: payload.session_id,
            "ownerid@odata.bind": _owner_bind(owner_id, owner_entity_set),
        }
        if payload.preferred_callback_window:
            body["scheduledend"] = payload.preferred_callback_window
        return body

    # ----- Dataverse interaction helpers -----------------------------------

    def _idempotent_create(
        self,
        *,
        entity: str,
        idempotency_field: str,
        idempotency_value: str,
        body: dict[str, object],
    ) -> str:
        """FR-024 — pre-query for an existing record with this idempotency key; if
        found, return its id. Otherwise POST and return the new record id."""
        existing = (
            self._client.get(
                entity,
                params={
                    "$filter": f"{idempotency_field} eq '{idempotency_value}'",
                    "$top": "1",
                },
            )
            .json()
            .get("value", [])
        )
        if existing:
            return str(existing[0].get(f"{entity}id"))
        response = self._client.post(entity, json=body)
        entity_uri = response.headers.get("OData-EntityId", "")
        return _parse_record_id_from_uri(entity_uri)

    def _fetch_queue_last_session(self, entity: str, queue_item_id: str) -> str | None:
        last_session_field = self._t.logical_name("queue.last_session_id")
        rows = (
            self._client.get(
                entity,
                params={
                    "$filter": f"{self._t.mapping.entities['queue_item'].primary_id or f'{entity}id'} "
                    f"eq {queue_item_id}",
                    "$select": last_session_field,
                    "$top": "1",
                },
            )
            .json()
            .get("value", [])
        )
        if not rows:
            return None
        value = rows[0].get(last_session_field)
        return None if value is None else str(value)

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
        entity = self._t.entity_logical_name("queue_item")
        primary_id = self._t.mapping.entities["queue_item"].primary_id or f"{entity}id"
        rows = (
            self._client.get(
                entity,
                params={
                    "$filter": f"{primary_id} eq {queue_item_id}",
                    "$select": override_field,
                    "$top": "1",
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
        """
        for entity, entity_set, extra_filter in (
            ("systemuser", "systemusers", " and isdisabled eq false"),
            ("team", "teams", ""),
        ):
            try:
                rows = (
                    self._client.get(
                        entity,
                        params={
                            "$filter": f"{entity}id eq {owner_id}{extra_filter}",
                            "$select": f"{entity}id",
                            "$top": "1",
                        },
                    )
                    .json()
                    .get("value", [])
                )
            except PermanentDataverseError:
                continue
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
        run_status: RunStatus = RunStatus.IN_PROGRESS,
    ) -> None:
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
                run_status=run_status,
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
    "DataverseWriteBackAdapter",
    "DataverseWriteBackError",
    "MappingError",
)
