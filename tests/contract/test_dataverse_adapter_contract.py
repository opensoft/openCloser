"""Contract test — `DataverseWriteBackAdapter` satisfies the unchanged Slice 1
`WriteBackAdapter` interface (SC-011).

Drives the adapter once per Disposition with the orchestrator's per-disposition
emission map and verifies it produces the correct Dataverse interactions for every
one of the 11 final dispositions.

Source of truth for the emission map and `new_status` table:
specs/001-mock-call-mock-crm/contracts/crm-writeback.md.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from opencloser.crm.base import WriteBackAdapter
from opencloser.crm.dataverse.adapter import DataverseWriteBackAdapter
from opencloser.crm.dataverse.mapping import MappingTranslator, load_mapping
from opencloser.models import (
    CallableStatus,
    Disposition,
    HumanReviewReason,
    PhoneCallActivityPayload,
    QueueItem,
    QueueStatusUpdatePayload,
    RetryConfig,
    Session,
    SessionState,
    TaskOwnersConfig,
    TaskPayload,
)
from opencloser.state import store
from tests.fixtures.dataverse.fake import DataverseFake
from tests.fixtures.dataverse.helpers import fake_for_mapping

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAPPING_FIXTURE = _REPO_ROOT / "tests/fixtures/dataverse/dataverse_mapping.json"

_T = "2026-05-22T16:00:00.000Z"
_QID = "q-contract-0001"
_SID = "ses_contract_0001"
_RETRY = RetryConfig(max_retries=0, backoff_seconds=[1.0], retry_after_cap_seconds=30.0)

# Orchestrator's FR-031 emission map — mirrored here as the contract surface (see
# crm-writeback.md). For each disposition: (emits_phone_call_activity, emits_task,
# task_kind | None, new_status).
_EMISSION_MAP: dict[Disposition, tuple[bool, bool, str | None, CallableStatus]] = {
    Disposition.INTERESTED_CALLBACK_REQUESTED: (True, True, "callback", CallableStatus.READY),
    Disposition.INTERESTED_EMAIL_CAPTURED: (True, True, "callback", CallableStatus.COMPLETED),
    Disposition.NEEDS_HUMAN_REVIEW: (True, True, "review", CallableStatus.BLOCKED),
    Disposition.NOT_INTERESTED: (True, False, None, CallableStatus.COMPLETED),
    Disposition.CALL_BACK_LATER: (True, True, "callback", CallableStatus.READY),
    Disposition.WRONG_NUMBER: (True, False, None, CallableStatus.BLOCKED),
    Disposition.NO_ANSWER: (True, False, None, CallableStatus.READY),
    Disposition.VOICEMAIL: (True, False, None, CallableStatus.READY),
    Disposition.DO_NOT_CALL: (True, False, None, CallableStatus.DNC),
    Disposition.FAILED: (True, False, None, CallableStatus.READY),
    Disposition.BLOCKED: (False, False, None, CallableStatus.READY),  # status unchanged
}

assert set(_EMISSION_MAP) == set(Disposition.__members__.values()), (
    "contract test must cover every Disposition"
)


def _seed_queue_row(records: dict[str, list[dict]], override_owner: str | None = None) -> None:
    row = {
        "medx_callqueueitemid": _QID,
        "_medx_accountid_value": "a-0001",
        "medx_phonenumber": "+15305551234",
        "medx_timezone": "America/Los_Angeles",
        "medx_attemptcount": 0,
        "medx_maxattempts": 5,
        "medx_donotcall": False,
        "medx_callstatus": 0,
        "medx_lastdisposition": None,
        "medx_lastsessionid": None,
        "medx_lasterror": None,
        "medx_nextattemptat": "2026-05-22T16:00:00.000Z",
        "_medx_campaignid_value": "alf-q2-davis",
        "medx_assignedownerid": override_owner,
    }
    records.setdefault("medx_callqueueitem", []).append(row)


def _seed_local_state(conn: sqlite3.Connection, disposition: Disposition) -> None:
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


def _seed_default_owners(records: dict[str, list[dict]]) -> None:
    """Seed the configured default owner ids as active enabled systemusers — the
    adapter blocks Task emission unless the default verifies (FR-025)."""
    existing = {row.get("systemuserid") for row in records.get("systemuser", [])}
    for owner in ("owner-callback-id", "owner-review-id"):
        if owner not in existing:
            records.setdefault("systemuser", []).append(
                {"systemuserid": owner, "isdisabled": False}
            )


def _adapter(
    conn: sqlite3.Connection, records: dict[str, list[dict]]
) -> tuple[DataverseWriteBackAdapter, DataverseFake]:
    mapping = load_mapping(_MAPPING_FIXTURE)
    _seed_default_owners(records)
    fake = fake_for_mapping(mapping, records)
    adapter = DataverseWriteBackAdapter(
        conn=conn,
        client=fake.client(_RETRY),
        translator=MappingTranslator(mapping),
        task_owners=TaskOwnersConfig(callback="owner-callback-id", review="owner-review-id"),
    )
    return adapter, fake


def _phone_call(disposition: Disposition) -> PhoneCallActivityPayload:
    return PhoneCallActivityPayload(
        session_id=_SID,
        queue_item_id=_QID,
        mock_provider_call_id="call_contract_x",
        persona_version="alf-appointment-setter@0.1.0",
        final_disposition=disposition,
        summary=f"Disposition: {disposition.value}",
        started_at=_T,
        ended_at=_T,
    )


def _queue_status(new_status: CallableStatus, reason: str) -> QueueStatusUpdatePayload:
    return QueueStatusUpdatePayload(
        session_id=_SID,
        queue_item_id=_QID,
        previous_status=CallableStatus.READY,
        new_status=new_status,
        transition_reason=reason,
        transition_at=_T,
    )


def _task(task_kind: str) -> TaskPayload:
    if task_kind == "callback":
        return TaskPayload(
            task_id="task_x",
            session_id=_SID,
            queue_item_id=_QID,
            task_kind="callback",
            subject="Callback follow-up",
            preferred_callback_window="Thursday 14:00",
            captured_email="contact@example.com",
            persona_version="alf-appointment-setter@0.1.0",
            created_at=_T,
        )
    return TaskPayload(
        task_id="task_x",
        session_id=_SID,
        queue_item_id=_QID,
        task_kind="review",
        subject="Review escalation",
        reason_code=HumanReviewReason.UNCERTAIN_ROLE,
        persona_version="alf-appointment-setter@0.1.0",
        created_at=_T,
    )


# ---------------------------------------------------------------------------
# Protocol conformance — runtime-checkable WriteBackAdapter (SC-011 / FR-016)
# ---------------------------------------------------------------------------


def test_adapter_satisfies_writeback_protocol(tmp_state_db: sqlite3.Connection) -> None:
    adapter, _ = _adapter(tmp_state_db, {})
    assert isinstance(adapter, WriteBackAdapter)


# ---------------------------------------------------------------------------
# Per-disposition contract — emission map + new_status (SC-011)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("disposition", list(_EMISSION_MAP.keys()))
def test_per_disposition_emission_matches_contract(
    tmp_state_db: sqlite3.Connection, disposition: Disposition
) -> None:
    """For every disposition the orchestrator may emit, the adapter calls the right
    Dataverse operations: POST phonecall iff phone_call_activity emits, PATCH the
    queue row with the contract-mandated new_status integer, POST task iff a task
    emits."""
    emits_pca, emits_task, task_kind, new_status = _EMISSION_MAP[disposition]

    _seed_local_state(tmp_state_db, disposition)
    records: dict[str, list[dict]] = {"account": [{"accountid": "a-0001", "name": "ALF"}]}
    _seed_queue_row(records)
    adapter, fake = _adapter(tmp_state_db, records)

    # Slice 1 orchestrator dictates what the adapter receives — mirror that here.
    if emits_pca:
        adapter.emit_phone_call_activity(_phone_call(disposition))
    transition_reason = (
        "blocked_by_eligibility: a" if disposition is Disposition.BLOCKED else disposition.value
    )
    adapter.emit_queue_status_update(_queue_status(new_status, transition_reason))
    if emits_task and task_kind is not None:
        adapter.emit_task(_task(task_kind))

    # Phone Call activity: created iff the map says so.
    phonecall_creates = [body for entity, body in fake.created if entity == "phonecall"]
    assert (len(phonecall_creates) == 1) is emits_pca, (
        f"phone_call_activity emission mismatch for {disposition.value}"
    )
    if emits_pca:
        assert phonecall_creates[0]["medx_idempotencykey"] == _SID

    # Queue PATCH always happens (FR-029 — exactly one queue_status_update per session).
    queue_patches = [
        changes for entity, _id, changes in fake.patched if entity == "medx_callqueueitem"
    ]
    assert len(queue_patches) == 1, f"expected exactly one queue PATCH for {disposition.value}"
    patch = queue_patches[0]

    # new_status integer matches the contract table.
    mapping = load_mapping(_MAPPING_FIXTURE)
    expected_status_int = mapping.option_sets[f"queue_status.{new_status.value}"].value
    assert patch["medx_callstatus"] == expected_status_int, (
        f"new_status integer for {disposition.value} should map to "
        f"{new_status.value}={expected_status_int}, got {patch['medx_callstatus']}"
    )

    # Only approved-update fields appear in the PATCH body (FR-003).
    translator = MappingTranslator(mapping)
    approved = translator.approved_update_logical_names()
    assert set(patch.keys()) <= approved

    # Task: created iff the map says so.
    task_creates = [body for entity, body in fake.created if entity == "task"]
    assert (len(task_creates) == 1) is emits_task, f"task emission mismatch for {disposition.value}"
    if emits_task:
        body = task_creates[0]
        assert body["medx_idempotencykey"] == _SID
        # Owner falls back to the default for the task kind when no override exists.
        expected_owner = "owner-callback-id" if task_kind == "callback" else "owner-review-id"
        assert body["ownerid@odata.bind"] == f"/systemusers({expected_owner})"


# ---------------------------------------------------------------------------
# Idempotency — emit_* are safe to repeat (FR-024)
# ---------------------------------------------------------------------------


def test_emit_phone_call_activity_is_idempotent(tmp_state_db: sqlite3.Connection) -> None:
    """A second emit for the same session must not create a duplicate phonecall — the
    adapter's pre-query returns the existing record."""
    _seed_local_state(tmp_state_db, Disposition.INTERESTED_CALLBACK_REQUESTED)
    records: dict[str, list[dict]] = {"account": [{"accountid": "a-0001", "name": "ALF"}]}
    _seed_queue_row(records)
    adapter, fake = _adapter(tmp_state_db, records)
    payload = _phone_call(Disposition.INTERESTED_CALLBACK_REQUESTED)

    adapter.emit_phone_call_activity(payload)
    adapter.emit_phone_call_activity(payload)

    assert sum(1 for e, _ in fake.created if e == "phonecall") == 1


def test_emit_task_belt_and_suspenders_blocks_excluded_dispositions(
    tmp_state_db: sqlite3.Connection,
) -> None:
    """FR-018 — emit_task is a no-op for excluded dispositions, mirroring the Slice 1
    MockWriteBackAdapter guard."""
    _seed_local_state(tmp_state_db, Disposition.DO_NOT_CALL)
    records: dict[str, list[dict]] = {"account": [{"accountid": "a-0001", "name": "ALF"}]}
    _seed_queue_row(records)
    adapter, fake = _adapter(tmp_state_db, records)
    adapter.emit_task(_task("callback"))
    assert not [b for e, b in fake.created if e == "task"]


def test_owner_override_falls_back_with_warning_when_unverifiable(
    tmp_state_db: sqlite3.Connection,
) -> None:
    """An override id that does not resolve to a systemuser/team is dropped; the
    default owner is written and an operator-visible warning is recorded (FR-025)."""
    _seed_local_state(tmp_state_db, Disposition.INTERESTED_CALLBACK_REQUESTED)
    records: dict[str, list[dict]] = {"account": [{"accountid": "a-0001", "name": "ALF"}]}
    _seed_queue_row(records, override_owner="unknown-user-id")
    adapter, fake = _adapter(tmp_state_db, records)

    adapter.emit_task(_task("callback"))

    task_body = next(b for e, b in fake.created if e == "task")
    assert task_body["ownerid@odata.bind"] == "/systemusers(owner-callback-id)"
    warnings = adapter.warnings()
    assert any(w.code == "task_owner_override_unverifiable" for w in warnings)


def test_owner_override_used_when_verifiable(tmp_state_db: sqlite3.Connection) -> None:
    """A verified override owner (an active enabled systemuser) is written through."""
    _seed_local_state(tmp_state_db, Disposition.INTERESTED_CALLBACK_REQUESTED)
    records: dict[str, list[dict]] = {
        "account": [{"accountid": "a-0001", "name": "ALF"}],
        "systemuser": [{"systemuserid": "approved-user-id", "isdisabled": False}],
    }
    _seed_queue_row(records, override_owner="approved-user-id")
    adapter, fake = _adapter(tmp_state_db, records)

    adapter.emit_task(_task("callback"))

    task_body = next(b for e, b in fake.created if e == "task")
    assert task_body["ownerid@odata.bind"] == "/systemusers(approved-user-id)"
    assert adapter.warnings() == []


def test_owner_override_skips_disabled_systemuser(tmp_state_db: sqlite3.Connection) -> None:
    """A disabled systemuser MUST NOT be honored as an override — the override is
    treated as unverifiable and the run falls back to the default (FR-025)."""
    _seed_local_state(tmp_state_db, Disposition.INTERESTED_CALLBACK_REQUESTED)
    records: dict[str, list[dict]] = {
        "account": [{"accountid": "a-0001", "name": "ALF"}],
        "systemuser": [{"systemuserid": "disabled-user-id", "isdisabled": True}],
    }
    _seed_queue_row(records, override_owner="disabled-user-id")
    adapter, fake = _adapter(tmp_state_db, records)

    adapter.emit_task(_task("callback"))

    task_body = next(b for e, b in fake.created if e == "task")
    assert task_body["ownerid@odata.bind"] == "/systemusers(owner-callback-id)"
    assert any(w.code == "task_owner_override_unverifiable" for w in adapter.warnings())


def test_owner_override_resolved_team_binds_to_teams(tmp_state_db: sqlite3.Connection) -> None:
    """An override resolved as a team binds to `/teams(<id>)`, not /systemusers."""
    _seed_local_state(tmp_state_db, Disposition.INTERESTED_CALLBACK_REQUESTED)
    records: dict[str, list[dict]] = {
        "account": [{"accountid": "a-0001", "name": "ALF"}],
        "team": [{"teamid": "approved-team-id"}],
    }
    _seed_queue_row(records, override_owner="approved-team-id")
    adapter, fake = _adapter(tmp_state_db, records)

    adapter.emit_task(_task("callback"))

    task_body = next(b for e, b in fake.created if e == "task")
    assert task_body["ownerid@odata.bind"] == "/teams(approved-team-id)"
    assert adapter.warnings() == []


def test_task_blocked_when_default_owner_unverifiable(tmp_state_db: sqlite3.Connection) -> None:
    """If the configured default owner cannot be verified as an active enabled user
    or team, Task emission is blocked — surfaced as `DataverseWriteBackError`
    (and a `crm_correlations(write_status=failed)` row + a warning) rather than
    silently completing a run that should have produced a Task (FR-025)."""
    from opencloser.crm.dataverse.adapter import DataverseWriteBackError

    mapping = load_mapping(_MAPPING_FIXTURE)
    _seed_local_state(tmp_state_db, Disposition.INTERESTED_CALLBACK_REQUESTED)
    records: dict[str, list[dict]] = {"account": [{"accountid": "a-0001", "name": "ALF"}]}
    _seed_queue_row(records)  # no override
    # Deliberately do NOT seed the default systemuser/team — _seed_default_owners
    # would add it, so build the fake directly here.
    fake = fake_for_mapping(mapping, records)
    adapter = DataverseWriteBackAdapter(
        conn=tmp_state_db,
        client=fake.client(_RETRY),
        translator=MappingTranslator(mapping),
        task_owners=TaskOwnersConfig(callback="missing-owner-id", review="missing-review-id"),
    )

    with pytest.raises(DataverseWriteBackError, match="no verifiable default or override owner"):
        adapter.emit_task(_task("callback"))

    # No Task created and the unverifiable-default warning is recorded.
    assert [b for e, b in fake.created if e == "task"] == []
    assert any(w.code == "task_owner_default_unverifiable" for w in adapter.warnings())
    # The failure is staged in memory; the runner persists it after the
    # orchestrator's transaction rolls back. Drive the flush here directly
    # to verify the row that downstream resume/audit will see.
    adapter.flush_pending_failures()
    rows = tmp_state_db.execute(
        "SELECT write_status FROM crm_correlations WHERE session_id = ? AND record_kind = ?;",
        (_SID, "task"),
    ).fetchall()
    assert [r["write_status"] for r in rows] == ["failed"]


def test_build_writeback_assembles_aggregate(tmp_state_db: sqlite3.Connection) -> None:
    _seed_local_state(tmp_state_db, Disposition.INTERESTED_CALLBACK_REQUESTED)
    records: dict[str, list[dict]] = {"account": [{"accountid": "a-0001", "name": "ALF"}]}
    _seed_queue_row(records)
    adapter, _ = _adapter(tmp_state_db, records)
    adapter.emit_phone_call_activity(_phone_call(Disposition.INTERESTED_CALLBACK_REQUESTED))
    adapter.emit_queue_status_update(
        _queue_status(CallableStatus.READY, "interested_callback_requested")
    )
    adapter.emit_task(_task("callback"))

    wb = adapter.build_writeback(_SID)
    assert wb.session_id == _SID
    assert wb.phone_call_activity is not None
    assert wb.queue_status_update is not None
    assert wb.task is not None
    # Slice 2 stamps assigned_to on the task aggregate.
    assert wb.task.assigned_to == "owner-callback-id"


def test_build_writeback_raises_without_queue_status(tmp_state_db: sqlite3.Connection) -> None:
    _seed_local_state(tmp_state_db, Disposition.INTERESTED_CALLBACK_REQUESTED)
    records: dict[str, list[dict]] = {"account": [{"accountid": "a-0001", "name": "ALF"}]}
    _seed_queue_row(records)
    adapter, _ = _adapter(tmp_state_db, records)
    with pytest.raises(KeyError):
        adapter.build_writeback(_SID)
