"""Unit tests for `src/opencloser/crm/dataverse/adapter.py` (T048).

Focused unit-level coverage of behaviors the contract test (T017) and the US1
integration test (T023) don't exercise granularly:

1. Owner-override decision logic — specifically the unverifiable-default branch
   of FR-025, which raises `DataverseWriteBackError` rather than silently
   completing without writing a required Task.
2. Idempotency-key stamping — verifies the field name comes from the mapping
   (`phone_call.idempotency_key` / `task.idempotency_key`) and the stamped
   value is the session ID, both in the pre-query filter and in the create
   body (FR-024).
3. Dry-run capture path — asserts zero `get`/`post`/`patch` calls and that
   planned payloads are returned via `build_writeback()` (FR-031).
4. `preserve_if_present` filtering — asserts the queue-status PATCH body
   contains only approved-update fields and never includes a
   `preserve_if_present` logical name (FR-003).

These tests use `unittest.mock.MagicMock` for `DataverseClient` so adapter
logic is exercised in isolation from the in-process fake; the mapping
translator, state store, and Pydantic models are the real implementations.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from opencloser.crm.dataverse.adapter import (
    DataverseWriteBackAdapter,
    DataverseWriteBackError,
)
from opencloser.crm.dataverse.mapping import MappingTranslator, load_mapping
from opencloser.models import (
    CallableStatus,
    Disposition,
    PhoneCallActivityPayload,
    QueueItem,
    QueueStatusUpdatePayload,
    Session,
    SessionState,
    TaskOwnersConfig,
    TaskPayload,
)
from opencloser.state import store

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAPPING_FIXTURE = _REPO_ROOT / "tests/fixtures/dataverse/dataverse_mapping.json"

_T = "2026-05-22T16:00:00.000Z"
_SID = "ses_unit_0001"
_QID = "q-unit-0001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_adapter(
    conn: sqlite3.Connection,
    *,
    client: MagicMock,
    dry_run: bool = False,
    task_owners: TaskOwnersConfig | None = None,
) -> DataverseWriteBackAdapter:
    mapping = load_mapping(_MAPPING_FIXTURE)
    return DataverseWriteBackAdapter(
        conn=conn,
        client=client,
        translator=MappingTranslator(mapping),
        task_owners=task_owners
        or TaskOwnersConfig(callback="owner-callback-id", review="owner-review-id"),
        now_utc_ms=lambda: _T,
        dry_run=dry_run,
    )


def _empty_get_client() -> MagicMock:
    """Mock client whose GET always returns an empty `value` list (no rows)."""
    client = MagicMock()
    client.get.return_value.json.return_value = {"value": []}
    client.post.return_value.headers = {
        "OData-EntityId": (
            "https://fake.crm.dynamics.com/api/data/v9.2/x(00000000-0000-0000-0000-000000000001)"
        )
    }
    return client


def _seed_session(conn: sqlite3.Connection, disposition: Disposition) -> None:
    store.insert_queue_item(
        conn,
        QueueItem(
            queue_item_id=_QID,
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
            session_id=_SID,
            queue_item_id=_QID,
            state=SessionState.FINALIZED,
            final_disposition=disposition,
            started_at=_T,
            ended_at=_T,
        ),
    )


def _phone_call_payload() -> PhoneCallActivityPayload:
    return PhoneCallActivityPayload(
        session_id=_SID,
        queue_item_id=_QID,
        mock_provider_call_id="call_unit_x",
        persona_version="alf-appointment-setter@0.1.0",
        final_disposition=Disposition.INTERESTED_CALLBACK_REQUESTED,
        summary="Disposition: interested_callback_requested",
        started_at=_T,
        ended_at=_T,
    )


def _queue_status_payload() -> QueueStatusUpdatePayload:
    return QueueStatusUpdatePayload(
        session_id=_SID,
        queue_item_id=_QID,
        previous_status=CallableStatus.READY,
        new_status=CallableStatus.COMPLETED,
        transition_reason="interested_callback_requested",
        transition_at=_T,
    )


def _task_payload(task_kind: str = "callback") -> TaskPayload:
    return TaskPayload(
        task_id="task_unit_x",
        session_id=_SID,
        queue_item_id=_QID,
        task_kind=task_kind,
        subject="Callback follow-up",
        preferred_callback_window="Thursday 14:00",
        captured_email="contact@example.com",
        persona_version="alf-appointment-setter@0.1.0",
        created_at=_T,
    )


# ---------------------------------------------------------------------------
# (1) Owner-override decision logic — unverifiable-default branch (FR-025)
# ---------------------------------------------------------------------------


class TestOwnerOverrideUnverifiableDefault:
    """Coverage gap left by the contract test, which always seeds the configured
    default as an active enabled systemuser. These tests exercise the path where
    the default itself fails to verify."""

    def test_unverifiable_default_raises_and_warns_and_writes_no_task(
        self, tmp_state_db: sqlite3.Connection
    ) -> None:
        """Spec §Definitions §Approved owner override: when the configured default
        is not an active enabled systemuser/team, `_resolve_task_owner` returns
        None; `emit_task` then raises `DataverseWriteBackError` so the run does
        not silently complete without writing the required follow-up Task."""
        _seed_session(tmp_state_db, Disposition.INTERESTED_CALLBACK_REQUESTED)
        client = _empty_get_client()
        adapter = _build_adapter(tmp_state_db, client=client)

        with pytest.raises(DataverseWriteBackError, match="FR-025"):
            adapter.emit_task(_task_payload("callback"))

        warnings = adapter.warnings()
        assert any(w.code == "task_owner_default_unverifiable" for w in warnings), (
            f"expected task_owner_default_unverifiable warning, got {warnings}"
        )
        # No POST issued — Task creation was blocked before the create call.
        assert client.post.call_count == 0

    def test_unverifiable_override_and_default_records_both_warnings(
        self, tmp_state_db: sqlite3.Connection
    ) -> None:
        """When the override resolves to an ID that exists on the queue row but
        verifies as neither systemuser nor team, AND the default also fails to
        verify, BOTH warnings are recorded and `emit_task` raises."""
        _seed_session(tmp_state_db, Disposition.INTERESTED_CALLBACK_REQUESTED)

        # First GET (override lookup on queue row): return an override ID.
        # Every subsequent GET (systemuser + team lookups for override AND
        # default): return empty. The override ID exists on the row but
        # resolves nowhere; the default also has no matching systemuser/team.
        override_row = [{"medx_assignedownerid": "unknown-id"}]
        responses = [{"value": override_row}] + [{"value": []}] * 10
        client = MagicMock()
        client.get.return_value.json.side_effect = responses
        client.post.return_value.headers = {
            "OData-EntityId": "https://fake.crm.dynamics.com/api/data/v9.2/x(g)"
        }
        adapter = _build_adapter(tmp_state_db, client=client)

        with pytest.raises(DataverseWriteBackError, match="FR-025"):
            adapter.emit_task(_task_payload("callback"))

        codes = {w.code for w in adapter.warnings()}
        assert "task_owner_override_unverifiable" in codes
        assert "task_owner_default_unverifiable" in codes
        assert client.post.call_count == 0


# ---------------------------------------------------------------------------
# (2) Idempotency-key stamping field selection (FR-024)
# ---------------------------------------------------------------------------


class TestIdempotencyKeyStamping:
    """Verifies the adapter stamps the session ID onto the Dataverse field whose
    logical name comes from the verified mapping artifact's
    `phone_call.idempotency_key` / `task.idempotency_key` entries. The contract
    test asserts the field is populated correctly under the fixture mapping;
    these tests pin down (a) the field selection is mapping-driven and (b) the
    pre-query filter targets the same field with the same value."""

    def test_emit_phone_call_activity_stamps_mapped_idempotency_field_with_session_id(
        self, tmp_state_db: sqlite3.Connection
    ) -> None:
        _seed_session(tmp_state_db, Disposition.INTERESTED_CALLBACK_REQUESTED)
        client = _empty_get_client()
        adapter = _build_adapter(tmp_state_db, client=client)

        adapter.emit_phone_call_activity(_phone_call_payload())

        # The mapping fixture maps `phone_call.idempotency_key` →
        # `medx_idempotencykey`. The stamped value must be the session ID.
        body = client.post.call_args.kwargs["json"]
        assert body["medx_idempotencykey"] == _SID
        # Pre-query filter must target the same logical name and the same value.
        pre_query_params = client.get.call_args.kwargs["params"]
        assert "medx_idempotencykey eq" in pre_query_params["$filter"]
        assert _SID in pre_query_params["$filter"]

    def test_emit_task_stamps_mapped_idempotency_field_with_session_id(
        self, tmp_state_db: sqlite3.Connection
    ) -> None:
        _seed_session(tmp_state_db, Disposition.INTERESTED_CALLBACK_REQUESTED)
        # Verifiable default: first GET (override lookup) empty → no override.
        # Next two GETs (systemusers for default verify): one row → match.
        responses = [
            {"value": []},  # override lookup — none
            {"value": [{"systemuserid": "owner-callback-id"}]},  # default systemuser match
            {"value": []},  # idempotency pre-query — no existing
        ]
        client = MagicMock()
        client.get.return_value.json.side_effect = responses
        client.post.return_value.headers = {
            "OData-EntityId": "https://fake.crm.dynamics.com/api/data/v9.2/tasks(g)"
        }
        adapter = _build_adapter(tmp_state_db, client=client)

        adapter.emit_task(_task_payload("callback"))

        body = client.post.call_args.kwargs["json"]
        assert body["medx_idempotencykey"] == _SID

    def test_emit_phone_call_activity_skips_post_when_pre_query_hits(
        self, tmp_state_db: sqlite3.Connection
    ) -> None:
        """FR-024 — when the idempotency pre-query returns a row, the adapter
        records the correlation from the existing row and issues NO POST."""
        _seed_session(tmp_state_db, Disposition.INTERESTED_CALLBACK_REQUESTED)
        client = MagicMock()
        client.get.return_value.json.return_value = {
            "value": [{"activityid": "existing-guid", "medx_idempotencykey": _SID}]
        }
        adapter = _build_adapter(tmp_state_db, client=client)

        adapter.emit_phone_call_activity(_phone_call_payload())

        assert client.post.call_count == 0


# ---------------------------------------------------------------------------
# (3) Dry-run capture path — zero HTTP calls, planned payloads returned
# ---------------------------------------------------------------------------


class TestDryRunCapture:
    """FR-031 + T048 — in dry-run mode, every `emit_*` translates the payload
    via the same mapping helpers as the write-enabled path but issues ZERO
    HTTP calls; the planned payload is captured for inclusion in
    `build_writeback()`."""

    def test_emit_phone_call_activity_dry_run_issues_no_http_calls(
        self, tmp_state_db: sqlite3.Connection
    ) -> None:
        _seed_session(tmp_state_db, Disposition.INTERESTED_CALLBACK_REQUESTED)
        client = _empty_get_client()
        adapter = _build_adapter(tmp_state_db, client=client, dry_run=True)

        adapter.emit_phone_call_activity(_phone_call_payload())

        assert client.get.call_count == 0
        assert client.post.call_count == 0
        assert client.patch.call_count == 0

    def test_emit_queue_status_update_dry_run_issues_no_http_calls(
        self, tmp_state_db: sqlite3.Connection
    ) -> None:
        _seed_session(tmp_state_db, Disposition.INTERESTED_CALLBACK_REQUESTED)
        client = _empty_get_client()
        adapter = _build_adapter(tmp_state_db, client=client, dry_run=True)

        adapter.emit_queue_status_update(_queue_status_payload())

        assert client.get.call_count == 0
        assert client.post.call_count == 0
        assert client.patch.call_count == 0

    def test_emit_task_dry_run_issues_no_http_calls_and_skips_owner_verification(
        self, tmp_state_db: sqlite3.Connection
    ) -> None:
        """Dry-run uses the configured default owner directly without verifying
        it against live systemusers/teams — the override lookup and the active-
        enabled verification would both require live Dataverse access."""
        _seed_session(tmp_state_db, Disposition.INTERESTED_CALLBACK_REQUESTED)
        client = _empty_get_client()
        adapter = _build_adapter(tmp_state_db, client=client, dry_run=True)

        adapter.emit_task(_task_payload("callback"))

        assert client.get.call_count == 0
        assert client.post.call_count == 0
        assert client.patch.call_count == 0

    def test_dry_run_all_three_emits_then_build_writeback_returns_planned_payloads(
        self, tmp_state_db: sqlite3.Connection
    ) -> None:
        """End-to-end dry-run capture: after emitting all three payloads, the
        aggregate exposed by `build_writeback` contains the planned content."""
        _seed_session(tmp_state_db, Disposition.INTERESTED_CALLBACK_REQUESTED)
        client = _empty_get_client()
        adapter = _build_adapter(tmp_state_db, client=client, dry_run=True)

        adapter.emit_phone_call_activity(_phone_call_payload())
        adapter.emit_queue_status_update(_queue_status_payload())
        adapter.emit_task(_task_payload("callback"))

        writeback = adapter.build_writeback(_SID)
        assert writeback.session_id == _SID
        assert writeback.phone_call_activity is not None
        assert writeback.queue_status_update is not None
        assert writeback.task is not None
        # Dry-run stamps the configured default owner without verification.
        assert writeback.task.assigned_to == "owner-callback-id"

    def test_dry_run_finalize_progress_is_a_noop(
        self, tmp_state_db: sqlite3.Connection
    ) -> None:
        """`finalize_progress` in dry-run writes no `writeback_progress` row —
        there is no CRM correlation and no resumable state to record."""
        from opencloser.models import RunStatus

        _seed_session(tmp_state_db, Disposition.INTERESTED_CALLBACK_REQUESTED)
        client = _empty_get_client()
        adapter = _build_adapter(tmp_state_db, client=client, dry_run=True)

        adapter.emit_phone_call_activity(_phone_call_payload())
        adapter.finalize_progress(_SID, run_status=RunStatus.COMPLETED)

        assert store.get_writeback_progress(tmp_state_db, _SID) is None


# ---------------------------------------------------------------------------
# (4) preserve_if_present filtering — non-approved fields never appear (FR-003)
# ---------------------------------------------------------------------------


class TestPreserveIfPresentFiltering:
    """FR-003 — the queue-status PATCH body MUST contain only approved-update
    logical names and MUST NOT contain any `preserve_if_present` field name."""

    def test_queue_status_patch_body_contains_only_approved_update_fields(
        self, tmp_state_db: sqlite3.Connection
    ) -> None:
        _seed_session(tmp_state_db, Disposition.INTERESTED_CALLBACK_REQUESTED)
        client = _empty_get_client()
        # The pre-query (`_fetch_queue_last_session`) returns no rows → adapter
        # proceeds to PATCH.
        adapter = _build_adapter(tmp_state_db, client=client)

        adapter.emit_queue_status_update(_queue_status_payload())

        body = client.patch.call_args.kwargs["json"]
        mapping = load_mapping(_MAPPING_FIXTURE)
        translator = MappingTranslator(mapping)
        approved = translator.approved_update_logical_names()
        preserve = set(translator.preserve_if_present())

        # Every key in the PATCH body must be an approved-update field.
        assert set(body.keys()) <= approved, (
            f"PATCH body contains non-approved fields: {set(body.keys()) - approved}"
        )
        # No preserve_if_present logical name may appear.
        assert set(body.keys()).isdisjoint(preserve), (
            f"PATCH body leaked preserve_if_present fields: "
            f"{set(body.keys()) & preserve}"
        )

    def test_dnc_flag_only_written_on_dnc_transition(
        self, tmp_state_db: sqlite3.Connection
    ) -> None:
        """The DNC field (`medx_donotcall`, an approved-update field) is set
        only when the transition is to dnc. A non-dnc transition leaves it
        absent from the PATCH body so an existing CRM DNC flag is preserved."""
        _seed_session(tmp_state_db, Disposition.INTERESTED_CALLBACK_REQUESTED)
        client = _empty_get_client()
        adapter = _build_adapter(tmp_state_db, client=client)

        adapter.emit_queue_status_update(_queue_status_payload())

        body = client.patch.call_args.kwargs["json"]
        assert "medx_donotcall" not in body
