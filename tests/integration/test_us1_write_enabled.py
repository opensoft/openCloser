"""US1 — Process one Dataverse queue item end-to-end with real CRM write-back.

End-to-end integration tests that exercise the full Slice 2 write-enabled loop
against the in-process Dataverse fake:

- happy path (interested_callback_requested) — SC-001
- alternate dispositions (interested_email_captured, needs_human_review,
  do_not_call) — SC-003 + SC-004
- blocked path (eligibility block, no call placed) — SC-008

The test driver reuses the runner so the exact write-enabled path the CLI runs is
under test (FR-014 — the orchestrator is unchanged).
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from opencloser.core.clock import FrozenClock
from opencloser.crm.dataverse.mapping import load_mapping
from opencloser.crm.dataverse.queue_loader import ExplicitId
from opencloser.models import (
    ArtifactsConfig,
    CallWindowConfig,
    DataverseConfig,
    DataverseMapping,
    Disposition,
    EligibilityConfig,
    PersonaConfig,
    RedactionPolicyConfig,
    RetryConfig,
    RunConfig,
    RunMode,
    Slice2Config,
    SliceConfig,
    StateConfig,
    TaskOwnersConfig,
)
from opencloser.slice2.runner import run_one_crm_item
from tests.fixtures.dataverse.fake import DataverseFake

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAPPING_FIXTURE = _REPO_ROOT / "tests/fixtures/dataverse/dataverse_mapping.json"
_CONVERSATIONS = _REPO_ROOT / "tests/fixtures/conversations"
_TRANSPORT_FIXTURES = _REPO_ROOT / "tests/fixtures/transport_events"

_QID = "22222222-2222-2222-2222-222222222222"
_OWNER_CALLBACK = "owner-callback-id"
_OWNER_REVIEW = "owner-review-id"

# A FrozenClock inside the configured call window for deterministic eligibility.
_CLOCK = FrozenClock(datetime(2026, 5, 22, 19, 0, 0, tzinfo=UTC))


def _slice1_config(artifact_dir: Path, db_path: Path) -> SliceConfig:
    return SliceConfig(
        call_window=CallWindowConfig(start="09:00", end="20:00"),
        eligibility=EligibilityConfig(max_attempts=5, default_timezone="America/Los_Angeles"),
        artifacts=ArtifactsConfig(dir=str(artifact_dir)),
        persona=PersonaConfig(version="alf-appointment-setter@0.1.0"),
        state=StateConfig(db=str(db_path)),
    )


def _slice2_config() -> Slice2Config:
    return Slice2Config(
        run=RunConfig(default_mode=RunMode.WRITE_ENABLED, campaign="alf-q2-davis"),
        dataverse=DataverseConfig(
            env_url="https://fake.crm.dynamics.com",
            mapping_artifact=str(_MAPPING_FIXTURE),
            callable_status="ready",
        ),
        retry=RetryConfig(max_retries=0, backoff_seconds=[1.0], retry_after_cap_seconds=30.0),
        task_owners=TaskOwnersConfig(callback=_OWNER_CALLBACK, review=_OWNER_REVIEW),
        redaction=RedactionPolicyConfig(policy="regex", retention="full", patterns=[]),
    )


def _entities(mapping: DataverseMapping) -> dict[str, set[str]]:
    entities: dict[str, set[str]] = {}
    for ekey, eref in mapping.entities.items():
        primary_id = eref.primary_id or f"{eref.logical_name}id"
        attrs = {primary_id}
        attrs |= {f.logical_name for f in mapping.fields.values() if f.entity == ekey}
        if ekey == "phone_call_activity":
            attrs |= {"subject", "description", "actualstart", "actualend"}
        if ekey == "task":
            attrs |= {"subject", "description", "ownerid"}
        entities[eref.logical_name] = attrs
    if mapping.task_owner_override_field:
        entities["medx_callqueueitem"].add(mapping.task_owner_override_field)
    entities["account"] = {"accountid", "name"}
    entities["systemuser"] = {"systemuserid", "isdisabled"}
    entities["team"] = {"teamid"}
    return entities


def _seed(
    *,
    phone: str = "+15305551234",
    status: int = 0,
    dnc: bool = False,
    override_owner: str | None = None,
) -> dict[str, list[dict]]:
    return {
        "account": [{"accountid": "11111111-1111-1111-1111-111111111111", "name": "Sunage ALF"}],
        "medx_callqueueitem": [
            {
                "medx_callqueueitemid": _QID,
                "medx_accountid": "11111111-1111-1111-1111-111111111111",
                "medx_phonenumber": phone,
                "medx_timezone": "America/Los_Angeles",
                "medx_attemptcount": 0,
                "medx_maxattempts": 5,
                "medx_donotcall": dnc,
                "medx_callstatus": status,
                "medx_lastdisposition": None,
                "medx_lastsessionid": None,
                "medx_lasterror": None,
                "medx_nextattemptat": "2026-05-22T16:00:00.000Z",
                "medx_assignedownerid": override_owner,
            }
        ],
        # FR-025 — the adapter blocks Task emission unless the default owner verifies
        # as an active enabled systemuser/team, so seed both default owners here.
        "systemuser": [
            {"systemuserid": _OWNER_CALLBACK, "isdisabled": False},
            {"systemuserid": _OWNER_REVIEW, "isdisabled": False},
        ],
    }


def _run(
    *,
    conn: sqlite3.Connection,
    fake: DataverseFake,
    transport_fixture: str,
    conversation_fixture: str | None,
    artifact_dir: Path,
):
    return run_one_crm_item(
        selector=ExplicitId(_QID),
        transport_fixture=_TRANSPORT_FIXTURES / f"{transport_fixture}.json",
        conversation_fixture=(
            _CONVERSATIONS / f"{conversation_fixture}.json" if conversation_fixture else None
        ),
        slice1_config=_slice1_config(artifact_dir, Path(":memory:")),
        slice2_config=_slice2_config(),
        client=fake.client(_slice2_config().retry),
        conn=conn,
        clock=_CLOCK,
    )


# ---------------------------------------------------------------------------
# SC-001 — happy path: interested_callback_requested
# ---------------------------------------------------------------------------


def test_us1_interested_callback_requested_writes_full_loop(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = DataverseFake(entities=_entities(mapping), records=_seed())
    report = _run(
        conn=tmp_state_db,
        fake=fake,
        transport_fixture="connected",
        conversation_fixture="interested_callback_requested",
        artifact_dir=tmp_artifact_dir,
    )

    # Exit status + disposition.
    assert report.exit_status == "completed"
    assert report.final_disposition is Disposition.INTERESTED_CALLBACK_REQUESTED
    assert report.session_id is not None
    assert report.queue_item_id == _QID
    assert report.artifact_dir is not None

    # Dataverse fake recorded: 1 phonecall create + 1 task create + 1 queue PATCH.
    phonecalls = [b for e, b in fake.created if e == "phonecalls"]
    tasks = [b for e, b in fake.created if e == "tasks"]
    queue_patches = [c for e, _id, c in fake.patched if e == "medx_callqueueitems"]
    assert len(phonecalls) == 1, "exactly one Phone Call activity per session"
    assert len(tasks) == 1, "one callback Task per session"
    assert len(queue_patches) == 1, "one queue-status PATCH per session"

    # Callback Task is assigned to the configured default owner (FR-025).
    assert tasks[0]["ownerid@odata.bind"] == f"/systemusers({_OWNER_CALLBACK})"

    # Queue PATCH carries the contract-mandated new_status = ready and the session id
    # stamp (idempotency anchor, FR-024).
    assert queue_patches[0]["medx_callstatus"] == 0  # queue_status.ready
    assert queue_patches[0]["medx_lastsessionid"] == report.session_id

    # crm_correlations rows recorded confirmed write-status for each kind.
    rows = tmp_state_db.execute(
        "SELECT record_kind, write_status FROM crm_correlations WHERE session_id = ?;",
        (report.session_id,),
    ).fetchall()
    kinds = {row["record_kind"]: row["write_status"] for row in rows}
    assert kinds == {
        "phone_call_activity": "confirmed",
        "queue_status": "confirmed",
        "task": "confirmed",
    }

    # writeback_progress.run_status terminal state.
    progress = tmp_state_db.execute(
        "SELECT run_status, phone_call_activity_done, queue_status_update_done, task_done "
        "FROM writeback_progress WHERE session_id = ?;",
        (report.session_id,),
    ).fetchone()
    assert progress["run_status"] == "completed"
    assert progress["phone_call_activity_done"] == 1
    assert progress["queue_status_update_done"] == 1
    assert progress["task_done"] == 1

    # Local session-result + writeback artifacts exist.
    for name in ("session-result.json", "writeback.json", "task.json"):
        assert (report.artifact_dir / name).exists(), f"missing artifact {name}"


# ---------------------------------------------------------------------------
# SC-003 — alternate dispositions
# ---------------------------------------------------------------------------


def test_us1_interested_email_captured_marks_completed(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = DataverseFake(entities=_entities(mapping), records=_seed())
    report = _run(
        conn=tmp_state_db,
        fake=fake,
        transport_fixture="connected",
        conversation_fixture="interested_email_captured",
        artifact_dir=tmp_artifact_dir,
    )
    assert report.exit_status == "completed"
    assert report.final_disposition is Disposition.INTERESTED_EMAIL_CAPTURED
    queue_patch = next(c for e, _id, c in fake.patched if e == "medx_callqueueitems")
    assert queue_patch["medx_callstatus"] == 2  # queue_status.completed


def test_us1_needs_human_review_writes_review_task(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = DataverseFake(entities=_entities(mapping), records=_seed())
    report = _run(
        conn=tmp_state_db,
        fake=fake,
        transport_fixture="connected",
        conversation_fixture="needs_human_review_uncertain_role",
        artifact_dir=tmp_artifact_dir,
    )
    assert report.exit_status == "completed"
    assert report.final_disposition is Disposition.NEEDS_HUMAN_REVIEW
    tasks = [b for e, b in fake.created if e == "tasks"]
    assert len(tasks) == 1
    # Review task is routed to the review owner (FR-025).
    assert tasks[0]["ownerid@odata.bind"] == f"/systemusers({_OWNER_REVIEW})"
    queue_patch = next(c for e, _id, c in fake.patched if e == "medx_callqueueitems")
    assert queue_patch["medx_callstatus"] == 3  # queue_status.blocked


def test_us1_do_not_call_sets_dnc_and_emits_no_task(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = DataverseFake(entities=_entities(mapping), records=_seed())
    report = _run(
        conn=tmp_state_db,
        fake=fake,
        transport_fixture="connected",
        conversation_fixture="do_not_call_mid_call",
        artifact_dir=tmp_artifact_dir,
    )
    assert report.exit_status == "completed"
    assert report.final_disposition is Disposition.DO_NOT_CALL
    # No Task is emitted for DNC (FR-018).
    assert [b for e, b in fake.created if e == "tasks"] == []
    queue_patch = next(c for e, _id, c in fake.patched if e == "medx_callqueueitems")
    assert queue_patch["medx_callstatus"] == 4  # queue_status.dnc
    assert queue_patch["medx_donotcall"] is True


# ---------------------------------------------------------------------------
# SC-008 — blocked path: eligibility blocks BEFORE any call is placed
# ---------------------------------------------------------------------------


def test_us1_blocked_by_dnc_does_not_place_call(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    mapping = load_mapping(_MAPPING_FIXTURE)
    # status=3 (blocked) so the eligibility evaluator rejects rule (f).
    fake = DataverseFake(entities=_entities(mapping), records=_seed(status=3))
    report = _run(
        conn=tmp_state_db,
        fake=fake,
        transport_fixture="connected",  # unused — eligibility blocks first
        conversation_fixture=None,
        artifact_dir=tmp_artifact_dir,
    )
    assert report.exit_status == "blocked"
    assert report.final_disposition is Disposition.BLOCKED
    # No Phone Call activity, no Task created. Exactly one queue PATCH carries the
    # block transition_reason via queue.last_error.
    assert [b for e, b in fake.created if e == "phonecalls"] == []
    assert [b for e, b in fake.created if e == "tasks"] == []
    queue_patches = [c for e, _id, c in fake.patched if e == "medx_callqueueitems"]
    assert len(queue_patches) == 1
    assert "blocked_by_eligibility" in str(queue_patches[0].get("medx_lasterror", ""))


# ---------------------------------------------------------------------------
# FR-034 — non-E.164 phone records a warning without changing exit status
# ---------------------------------------------------------------------------


def test_us1_non_e164_phone_records_warning(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = DataverseFake(entities=_entities(mapping), records=_seed(phone="555-1234"))
    report = _run(
        conn=tmp_state_db,
        fake=fake,
        transport_fixture="connected",
        conversation_fixture="interested_callback_requested",
        artifact_dir=tmp_artifact_dir,
    )
    # Exit status is unaffected (FR-034 is a warning, not a block).
    assert report.exit_status == "completed"
    assert any(w.code == "non_e164_phone" for w in report.warnings)
    # The queue PATCH carries the warning summary in last_error.
    queue_patch = next(c for e, _id, c in fake.patched if e == "medx_callqueueitems")
    assert "non_e164_phone" in str(queue_patch.get("medx_lasterror", ""))


# ---------------------------------------------------------------------------
# Empty-queue selector — clean no-op (FR-009)
# ---------------------------------------------------------------------------


def test_us1_empty_queue_is_clean_noop(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = DataverseFake(
        entities=_entities(mapping), records={"account": [], "medx_callqueueitem": []}
    )
    # The runner accepts a transport fixture path even though it will not be used.
    report = run_one_crm_item(
        selector=ExplicitId("does-not-exist"),
        transport_fixture=_TRANSPORT_FIXTURES / "connected.json",
        conversation_fixture=None,
        slice1_config=_slice1_config(tmp_artifact_dir, Path(":memory:")),
        slice2_config=_slice2_config(),
        client=fake.client(_slice2_config().retry),
        conn=tmp_state_db,
        clock=_CLOCK,
    )
    assert report.exit_status == "no-callable-item"
    # No Dataverse writes happened.
    assert fake.created == []
    assert fake.patched == []
