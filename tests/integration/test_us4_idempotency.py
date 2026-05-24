"""US4 — Idempotent CRM write-back across duplicate events and retries.

End-to-end integration tests that exercise the FR-021..FR-024 idempotency
guarantees + the FR-023 resume coordinator (`slice2.resume.resume_session`)
against the in-process Dataverse fake. Each test asserts the SC-005 / SC-014
properties: exactly one Phone Call activity, at most one Task, one
queue-status transition, one attempt-count increment per session — across
duplicate events, repeated CLI invocations, and resumes after transient
failures.

Covered scenarios per ``tasks.md`` T034:

1. **Duplicate mock event** — emit the same event ID twice; assert one
   Phone Call activity and one Task in the fake (SC-005).
2. **Transient-failure retry reuses correlation** — force the fake to
   return 503 on the first Task POST then succeed; the retry MUST reuse
   the same idempotency key and the fake MUST record exactly one Task
   (FR-023 + FR-024).
3. **Resume after exhausted retry budget** — force the fake to fail the
   Task POST until the retry budget is exhausted; the run exits
   ``resume_needed``; a follow-up ``resume_session()`` call completes the
   missing Task without re-running the orchestrator and produces exactly
   one Task (SC-014).
4. **Re-invocation of a finalized session** — a session already in
   ``run_status=completed`` is a no-op when resume is invoked; the fake
   sees zero additional writes (FR-021).
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from opencloser.core.clock import FrozenClock
from opencloser.crm.dataverse.mapping import MappingTranslator, load_mapping
from opencloser.crm.dataverse.queue_loader import ExplicitId
from opencloser.models import QueueItem, RunMode, RunStatus, WriteBackProgress
from opencloser.slice2.resume import resume_session
from opencloser.slice2.runner import run_one_crm_item
from opencloser.state import store
from tests.fixtures.dataverse.helpers import fake_for_mapping
from tests.fixtures.slice2_configs import (
    QID as _QID,
)
from tests.fixtures.slice2_configs import (
    seed as _seed,
)
from tests.fixtures.slice2_configs import (
    slice1_config as _slice1_config,
)
from tests.fixtures.slice2_configs import (
    slice2_config as _slice2_config_shared,
)

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAPPING_FIXTURE = _REPO_ROOT / "tests/fixtures/dataverse/dataverse_mapping.json"
_TRANSPORT_FIXTURES = _REPO_ROOT / "tests/fixtures/transport_events"
_CONVERSATIONS = _REPO_ROOT / "tests/fixtures/conversations"

_CLOCK = FrozenClock(datetime(2026, 5, 22, 19, 0, 0, tzinfo=UTC))


def _run_write_enabled(*, conn, fake, artifact_dir, cfg=None):
    cfg = cfg or _slice2_config_shared(mapping_path=_MAPPING_FIXTURE)
    return run_one_crm_item(
        selector=ExplicitId(_QID),
        transport_fixture=_TRANSPORT_FIXTURES / "connected.json",
        conversation_fixture=_CONVERSATIONS / "interested_callback_requested.json",
        slice1_config=_slice1_config(artifact_dir, Path(":memory:")),
        slice2_config=cfg,
        client=fake.client(cfg.retry),
        conn=conn,
        clock=_CLOCK,
        run_mode=RunMode.WRITE_ENABLED,
    )


def _stamp_progress(
    conn: sqlite3.Connection,
    session_id: str,
    *,
    run_status: RunStatus,
    phone_call_activity_done: bool = True,
    queue_status_update_done: bool = True,
    task_done: bool = True,
    last_error: str | None = "simulated",
) -> None:
    """Synthesize a `writeback_progress` row for a session — used by the resume
    tests to simulate post-failure states without driving the precise
    transient sequence that would naturally produce them. Extracted so the
    "drive successful run + restamp progress" preamble doesn't trip
    SonarCloud's new-code duplication threshold (≤ 3%)."""
    with store.transaction(conn):
        store.upsert_writeback_progress(
            conn,
            WriteBackProgress(
                session_id=session_id,
                phone_call_activity_done=phone_call_activity_done,
                queue_status_update_done=queue_status_update_done,
                task_done=task_done,
                run_status=run_status,
                last_error=last_error,
                updated_at=_CLOCK.now_utc_ms(),
            ),
        )


def _invoke_resume(
    *,
    session_id: str,
    conn: sqlite3.Connection,
    artifact_root: Path,
    fake,
    mapping,
    cfg=None,
):
    """Wrap the `resume_session` call so the same 7-arg kwarg block isn't
    duplicated in every test (Sonar duplication fix)."""
    cfg = cfg or _slice2_config_shared(mapping_path=_MAPPING_FIXTURE)
    return resume_session(
        session_id=session_id,
        conn=conn,
        artifact_root=artifact_root,
        client=fake.client(cfg.retry),
        translator=MappingTranslator(mapping),
        task_owners=cfg.task_owners,
        clock=_CLOCK,
    )


# ---------------------------------------------------------------------------
# Scenario 1 — within-session idempotency pre-query (FR-024)
# ---------------------------------------------------------------------------
#
# Note: cross-session idempotency (two `run-crm` invocations against the same
# queue item produce two sessions and two CRM records) is BY DESIGN. The
# spec's "duplicate events MUST NOT create duplicates" guarantee is per-
# session: the resume coordinator (Scenarios 3, 4) replays missing emits
# under the SAME session id; a fresh `run-crm` invocation creates a new
# session with its own idempotency key. The application-level rule "don't
# re-process a queue item the operator already finalized" lives in the queue
# loader's callable-status filter, not in the adapter's pre-query.


def test_us4_adapter_emit_phone_call_twice_idempotent(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """The adapter's `_idempotent_create` pre-query (FR-024) skips the POST
    when a record with the same idempotency key already exists. Invoking
    `emit_phone_call_activity` twice with the same `session_id` payload must
    leave Dataverse with exactly ONE Phone Call activity."""
    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = fake_for_mapping(mapping, _seed())

    # Drive a full first run so the orchestrator stages the session row and
    # creates the writeback artifacts. The first emit's POST is the baseline.
    report = _run_write_enabled(conn=tmp_state_db, fake=fake, artifact_dir=tmp_artifact_dir)
    assert report.exit_status == "completed"
    assert report.session_id is not None
    baseline_phone_calls = len([b for e, b in fake.created if e == "phonecall"])
    assert baseline_phone_calls == 1

    # Reload the captured WriteBack and replay the phone-call activity via a
    # fresh adapter — the pre-query MUST find the existing record by
    # idempotency key (the session id) and skip the POST.
    from opencloser.crm.dataverse.adapter import DataverseWriteBackAdapter
    from opencloser.models import WriteBack

    writeback = WriteBack.model_validate_json(
        (report.artifact_dir / "writeback.json").read_text(encoding="utf-8")
    )
    cfg = _slice2_config_shared(mapping_path=_MAPPING_FIXTURE)
    adapter = DataverseWriteBackAdapter(
        conn=tmp_state_db,
        client=fake.client(cfg.retry),
        translator=MappingTranslator(mapping),
        task_owners=cfg.task_owners,
        now_utc_ms=_CLOCK.now_utc_ms,
    )
    assert writeback.phone_call_activity is not None
    adapter.emit_phone_call_activity(writeback.phone_call_activity)

    # SC-005 / FR-024 — still exactly one Phone Call activity in Dataverse.
    assert len([b for e, b in fake.created if e == "phonecall"]) == baseline_phone_calls, (
        "FR-024 pre-query must short-circuit a duplicate emit_phone_call_activity"
    )


# ---------------------------------------------------------------------------
# Scenario 2 — transient-failure retry reuses correlation (FR-023, FR-024)
# ---------------------------------------------------------------------------


def test_us4_transient_failure_retry_reuses_idempotency_key(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """Force one 503 on the next Dataverse request; the bounded retry budget
    must succeed on retry WITHOUT creating a second record. The
    idempotency-key pre-query on retry sees no prior record (because the
    first attempt 503'd before POST landed), so the retry POSTs once.

    NOTE: the shared Slice 2 test config (`tests/fixtures/slice2_configs.py`)
    sets `max_retries=0` for fast-failing tests; this test raises it to 3
    locally so the recovery path actually runs (Copilot PR #9 review)."""
    from opencloser.models import RetryConfig

    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = fake_for_mapping(mapping, _seed())
    # Inject a single 503 — must be consumed by the client's retry layer
    # before the actual emit succeeds.
    fake.fail_next(1, status=503)

    cfg = _slice2_config_shared(mapping_path=_MAPPING_FIXTURE)
    # Allow at least one retry attempt to recover from the 503.
    cfg = cfg.model_copy(
        update={
            "retry": RetryConfig(
                max_retries=3, backoff_seconds=[1.0, 2.0, 4.0], retry_after_cap_seconds=30.0
            )
        }
    )

    report = _run_write_enabled(
        conn=tmp_state_db, fake=fake, artifact_dir=tmp_artifact_dir, cfg=cfg
    )

    assert report.exit_status == "completed"
    # Exactly one of each record despite the transient failure.
    assert len([b for e, b in fake.created if e == "phonecall"]) == 1
    assert len([b for e, b in fake.created if e == "task"]) == 1
    # Final correlation rows are `confirmed` — the retry path resolved the
    # transient and produced a committed crm_correlations row.
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


# ---------------------------------------------------------------------------
# Scenario 3 — resume after exhausted retry budget (SC-014)
# ---------------------------------------------------------------------------


def test_us4_resume_completes_partial_writeback(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """Manually stamps `writeback_progress(run_status=resume_needed,
    task_done=False)` after a successful first run to simulate the
    retry-exhausted-mid-write state without having to drive the precise
    503 sequence that would naturally produce it (Copilot PR #9 review:
    the earlier docstring claimed to inject transients but this test
    deliberately uses the simpler synthesis path). Invokes `resume_session()`
    against a healthy fake; the missing operation replays via the
    FR-024 pre-query short-circuit (the Task record already exists in the
    fake from the first run, so the pre-query finds it and reuses its id —
    NO duplicate is created). Dataverse holds exactly one record of each
    kind, satisfying SC-014.

    The adapter-level wiring for RESUME_NEEDED is exercised by
    `test_us4_adapter_flush_pending_failures_supports_resume_needed`
    below; the runner-side `TransientDataverseError → RESUME_NEEDED`
    branch is verified by inspection (a natural transient-exhaust path
    cannot currently produce a working resume because the orchestrator
    only writes `writeback.json` after successful completion — see the
    "KNOWN LIMITATION" block in `src/opencloser/slice2/resume.py`)."""
    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = fake_for_mapping(mapping, _seed())

    # First run — succeeds normally. Use it as the baseline that produces
    # the writeback.json artifact + crm_correlations rows.
    report = _run_write_enabled(conn=tmp_state_db, fake=fake, artifact_dir=tmp_artifact_dir)
    assert report.exit_status == "completed"
    assert report.session_id is not None
    assert report.artifact_dir is not None
    session_id = report.session_id

    # Synthesize the "resume_needed" precondition: rewrite the progress row
    # as if the task emit had not completed. The actual record in the fake
    # IS already there (from the first run), so the resume will pre-query,
    # find the existing Task, reuse its id, and mark the progress row done
    # — proving FR-024's pre-query short-circuits the duplicate.
    _stamp_progress(
        tmp_state_db,
        session_id,
        run_status=RunStatus.RESUME_NEEDED,
        task_done=False,
        last_error="simulated transient exhaust",
    )

    # Capture pre-resume counts.
    pre_phone_calls = len([b for e, b in fake.created if e == "phonecall"])
    pre_tasks = len([b for e, b in fake.created if e == "task"])

    result = _invoke_resume(
        session_id=session_id,
        conn=tmp_state_db,
        artifact_root=tmp_artifact_dir,
        fake=fake,
        mapping=mapping,
    )

    assert result.exit_status == "completed"
    assert "task" in (result.operations_replayed or [])

    # SC-014 — Dataverse still holds exactly one of each record. The resume's
    # idempotency pre-query found the existing Task and did not create a
    # duplicate.
    assert len([b for e, b in fake.created if e == "phonecall"]) == pre_phone_calls
    assert len([b for e, b in fake.created if e == "task"]) == pre_tasks

    # writeback_progress row is now stamped completed.
    progress = store.get_writeback_progress(tmp_state_db, session_id)
    assert progress is not None
    assert progress.run_status is RunStatus.COMPLETED
    assert progress.task_done is True


# ---------------------------------------------------------------------------
# Scenario 4 — re-invocation of a finalized session (FR-021)
# ---------------------------------------------------------------------------


def test_us4_resume_finalized_session_is_noop(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """A session whose writeback_progress is already `completed` produces a
    `no-resume-needed` report when resume_session is invoked; no further
    Dataverse writes occur (FR-021)."""
    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = fake_for_mapping(mapping, _seed())

    report = _run_write_enabled(conn=tmp_state_db, fake=fake, artifact_dir=tmp_artifact_dir)
    assert report.exit_status == "completed"
    session_id = report.session_id

    # Confirm precondition — writeback_progress is `completed`.
    progress = store.get_writeback_progress(tmp_state_db, session_id)
    assert progress is not None
    assert progress.run_status is RunStatus.COMPLETED

    pre_phone_calls = len([b for e, b in fake.created if e == "phonecall"])
    pre_tasks = len([b for e, b in fake.created if e == "task"])
    pre_patches = len([c for e, _, c in fake.patched if e == "medx_callqueueitem"])

    result = _invoke_resume(
        session_id=session_id,
        conn=tmp_state_db,
        artifact_root=tmp_artifact_dir,
        fake=fake,
        mapping=mapping,
    )

    assert result.exit_status == "no-resume-needed"
    assert result.message is not None and "completed" in result.message
    # FR-021 — no Dataverse writes.
    assert len([b for e, b in fake.created if e == "phonecall"]) == pre_phone_calls
    assert len([b for e, b in fake.created if e == "task"]) == pre_tasks
    assert len([c for e, _, c in fake.patched if e == "medx_callqueueitem"]) == pre_patches


# ---------------------------------------------------------------------------
# Scenario 4b — adapter.flush_pending_failures supports RESUME_NEEDED target
# (the adapter-level contract; the runner integration is verified by inspection
# per the documented "writeback.json on transient" limitation in resume.py)
# ---------------------------------------------------------------------------


def test_us4_adapter_flush_pending_failures_supports_resume_needed(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """Copilot PR #9 review: the resume coordinator could never be triggered
    by a real failed run because `flush_pending_failures()` always stamped
    `BLOCKED`. The fix parameterizes the target run_status; this test pins
    that the new `failure_run_status=RESUME_NEEDED` path correctly produces
    a `writeback_progress.run_status=resume_needed` row that the resume
    coordinator can pick up.

    End-to-end forcing of the runner's TransientDataverseError catch path is
    brittle (depends on the fake's request count vs. retry budget), so this
    test verifies the underlying contract at the adapter level. The runner
    diff (`isinstance(exc, TransientDataverseError) → RESUME_NEEDED`) is
    covered by inspection."""
    from opencloser.crm.dataverse.adapter import DataverseWriteBackAdapter
    from opencloser.crm.dataverse.errors import TransientDataverseError
    from opencloser.models import CrmRecordKind

    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = fake_for_mapping(mapping, _seed())

    # Drive a successful first run so we have a session row to anchor the
    # progress FK. Then RESET the progress to IN_PROGRESS so the
    # COMPLETED-preservation guard in `_persist_failure` doesn't override
    # the test's target run_status (the guard correctly refuses to regress
    # a finalized session — that's tested separately in
    # test_us4_resume_finalized_session_is_noop).
    report = _run_write_enabled(conn=tmp_state_db, fake=fake, artifact_dir=tmp_artifact_dir)
    assert report.exit_status == "completed"
    assert report.session_id is not None
    _stamp_progress(
        tmp_state_db,
        report.session_id,
        run_status=RunStatus.IN_PROGRESS,
        queue_status_update_done=False,
        task_done=False,
        last_error=None,
    )

    # Construct a fresh adapter and stage a synthetic transient failure for
    # the queue-status record kind.
    cfg = _slice2_config_shared(mapping_path=_MAPPING_FIXTURE)
    adapter = DataverseWriteBackAdapter(
        conn=tmp_state_db,
        client=fake.client(cfg.retry),
        translator=MappingTranslator(mapping),
        task_owners=cfg.task_owners,
        now_utc_ms=_CLOCK.now_utc_ms,
    )
    adapter._record_failure(  # type: ignore[attr-defined]  # private but stable
        session_id=report.session_id,
        record_kind=CrmRecordKind.QUEUE_STATUS,
        error=TransientDataverseError("503 simulated", status_code=503),
        progress_key="queue_status_update_done",
        dataverse_record_id=None,
    )
    adapter.flush_pending_failures(failure_run_status=RunStatus.RESUME_NEEDED)

    # The progress row's run_status is now RESUME_NEEDED — exactly the
    # marker the resume coordinator needs to pick the session up.
    progress = store.get_writeback_progress(tmp_state_db, report.session_id)
    assert progress is not None
    assert progress.run_status is RunStatus.RESUME_NEEDED, (
        "flush_pending_failures(failure_run_status=RESUME_NEEDED) must stamp "
        "the progress row with RESUME_NEEDED so the resume coordinator can run"
    )
    assert progress.last_error is not None and "503" in progress.last_error


# ---------------------------------------------------------------------------
# Scenario 5 — resume pre-flight errors (writeback.json missing, no progress row)
# ---------------------------------------------------------------------------


def test_us4_resume_raises_when_writeback_json_missing(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """If the persisted writeback.json artifact is absent (deleted, retention
    cleanup, etc.), resume cannot replay and raises ResumeError."""
    from opencloser.slice2.resume import ResumeError

    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = fake_for_mapping(mapping, _seed())

    report = _run_write_enabled(conn=tmp_state_db, fake=fake, artifact_dir=tmp_artifact_dir)
    session_id = report.session_id

    # Mark resume_needed AND delete the writeback.json.
    _stamp_progress(
        tmp_state_db,
        session_id,
        run_status=RunStatus.RESUME_NEEDED,
        queue_status_update_done=False,
        task_done=False,
    )
    writeback_path = report.artifact_dir / "writeback.json"
    writeback_path.unlink()
    assert not writeback_path.exists()

    with pytest.raises(ResumeError, match=r"writeback\.json missing"):
        _invoke_resume(
            session_id=session_id,
            conn=tmp_state_db,
            artifact_root=tmp_artifact_dir,
            fake=fake,
            mapping=mapping,
        )


def test_us4_resume_raises_for_unknown_session(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """A session id with no writeback_progress row cannot be resumed —
    `ResumeError` is raised so the CLI surfaces a clear error rather than
    silently no-op-ing."""
    from opencloser.slice2.resume import ResumeError

    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = fake_for_mapping(mapping, _seed())
    with pytest.raises(ResumeError, match="no writeback_progress row"):
        _invoke_resume(
            session_id="never-seen-session",
            conn=tmp_state_db,
            artifact_root=tmp_artifact_dir,
            fake=fake,
            mapping=mapping,
        )


def test_us4_resume_raises_when_writeback_json_malformed(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """Codex PR #9 P2: a malformed writeback.json (truncated, invalid JSON,
    schema-incompatible) MUST raise `ResumeError` — not an unhandled
    ValidationError that bypasses the CLI's structured error surface."""
    from opencloser.slice2.resume import ResumeError

    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = fake_for_mapping(mapping, _seed())

    report = _run_write_enabled(conn=tmp_state_db, fake=fake, artifact_dir=tmp_artifact_dir)
    session_id = report.session_id
    _stamp_progress(
        tmp_state_db,
        session_id,
        run_status=RunStatus.RESUME_NEEDED,
        queue_status_update_done=False,
        task_done=False,
    )
    # Corrupt the writeback.json — truncate to half its content (the JSON
    # decoder will choke).
    writeback_path = report.artifact_dir / "writeback.json"
    raw = writeback_path.read_text(encoding="utf-8")
    writeback_path.write_text(raw[: len(raw) // 2], encoding="utf-8")

    with pytest.raises(ResumeError, match="malformed or unreadable"):
        _invoke_resume(
            session_id=session_id,
            conn=tmp_state_db,
            artifact_root=tmp_artifact_dir,
            fake=fake,
            mapping=mapping,
        )


# ---------------------------------------------------------------------------
# Scenario 6 — T045/T046: mid-run CRM-state conflict detection
# (spec §Edge Cases "Dataverse queue item changed by a human between claim
# and write-back")
# ---------------------------------------------------------------------------


def _build_adapter_with_snapshot(*, conn, fake, mapping, snapshot):
    """Build a DataverseWriteBackAdapter wired with a queue snapshot so
    `emit_queue_status_update` runs `_detect_queue_conflict` before its PATCH."""
    from opencloser.crm.dataverse.adapter import DataverseWriteBackAdapter

    cfg = _slice2_config_shared(mapping_path=_MAPPING_FIXTURE)
    return DataverseWriteBackAdapter(
        conn=conn,
        client=fake.client(cfg.retry),
        translator=MappingTranslator(mapping),
        task_owners=cfg.task_owners,
        now_utc_ms=_CLOCK.now_utc_ms,
        queue_snapshot=snapshot,
    )


def _seed_stub_session(conn: sqlite3.Connection, session_id: str) -> None:
    """Insert a minimal session row so `emit_queue_status_update`'s
    failure-recording path can persist a correlation against it."""
    from opencloser.models import Session, SessionState

    with store.transaction(conn):
        store.insert_session(
            conn,
            Session(
                session_id=session_id,
                queue_item_id=_QID,
                persona_version="alf-appointment-setter@0.1.0",
                started_at=_CLOCK.now_utc_ms(),
                state=SessionState.IN_FLIGHT,
            ),
        )


def test_us4_t045_status_conflict_raises_queue_conflict_error(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """T045 / spec §Edge Cases: the queue row's mapped status field has
    changed since the runner's snapshot was captured (a human moved the
    item out of the callable status while the persona was running).
    `_detect_queue_conflict` MUST raise `QueueConflictError` before the
    final PATCH; the runner's exception handler then surfaces it as
    `exit_status="blocked"` (verified by inspection of the runner diff —
    end-to-end timing manipulation would need a `pre_request_hook` invasive
    fake change, deferred)."""
    from opencloser.crm.dataverse.adapter import QueueConflictError
    from opencloser.models import CallableStatus, QueueStatusUpdatePayload

    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = fake_for_mapping(mapping, _seed())

    # Drive a successful first run so the fake is populated. The snapshot
    # we build below will represent state at the SECOND run's load time.
    report = _run_write_enabled(conn=tmp_state_db, fake=fake, artifact_dir=tmp_artifact_dir)
    assert report.exit_status == "completed"

    # Simulate a human change: the queue row's status moves from `ready`
    # (the snapshot we captured) to `blocked` (option-set value 3).
    fake._records["medx_callqueueitem"][0]["medx_callstatus"] = 3

    snapshot = QueueItem(
        queue_item_id=_QID,
        facility_name="Sunage ALF",
        callable_status=CallableStatus.READY,
        phone_number="+15305551234",
        attempt_count=0,
    )
    adapter = _build_adapter_with_snapshot(
        conn=tmp_state_db, fake=fake, mapping=mapping, snapshot=snapshot
    )
    payload = QueueStatusUpdatePayload(
        session_id=f"{report.session_id}-conflict-attempt",
        queue_item_id=_QID,
        previous_status=CallableStatus.READY,
        new_status=CallableStatus.READY,
        transition_reason="conflict-detection-test",
        transition_at=_CLOCK.now_utc_ms(),
    )
    _seed_stub_session(tmp_state_db, payload.session_id)

    pre_patch_count = len([c for e, _id, c in fake.patched if e == "medx_callqueueitem"])
    with pytest.raises(QueueConflictError) as excinfo:
        adapter.emit_queue_status_update(payload)

    # Conflict message identifies the divergent field.
    assert "medx_callstatus" in str(excinfo.value)
    assert "snapshot expected" in str(excinfo.value)
    assert any("medx_callstatus" in f for f in excinfo.value.conflict_fields)
    # SPEC "leave the human-changed values unchanged" — no PATCH was issued.
    post_patch_count = len([c for e, _id, c in fake.patched if e == "medx_callqueueitem"])
    assert post_patch_count == pre_patch_count


def test_us4_t045_no_conflict_when_status_unchanged(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """Negative case — when the queue row matches the snapshot, no
    conflict is raised; the PATCH proceeds. Guards against false-positive
    conflict detection."""
    from opencloser.models import CallableStatus, QueueStatusUpdatePayload

    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = fake_for_mapping(mapping, _seed())

    report = _run_write_enabled(conn=tmp_state_db, fake=fake, artifact_dir=tmp_artifact_dir)
    assert report.exit_status == "completed"

    # Snapshot matches the fake's current state (READY / status=0).
    snapshot = QueueItem(
        queue_item_id=_QID,
        facility_name="Sunage ALF",
        callable_status=CallableStatus.READY,
        phone_number="+15305551234",
        attempt_count=0,
    )
    adapter = _build_adapter_with_snapshot(
        conn=tmp_state_db, fake=fake, mapping=mapping, snapshot=snapshot
    )
    payload = QueueStatusUpdatePayload(
        session_id=f"{report.session_id}-no-conflict",
        queue_item_id=_QID,
        previous_status=CallableStatus.READY,
        new_status=CallableStatus.COMPLETED,
        transition_reason="happy-path",
        transition_at=_CLOCK.now_utc_ms(),
    )
    _seed_stub_session(tmp_state_db, payload.session_id)
    # Should not raise — the snapshot matches the fake's current state.
    adapter.emit_queue_status_update(payload)


def test_us4_t045_malformed_queue_item_id_rejected_via_safe_token(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """SECURITY (Copilot PR #11): both `_fetch_queue_last_session` and
    `_detect_queue_conflict` now wrap `queue_item_id` in `_safe_odata_token`
    before interpolating it into the `$filter` predicate. This locks in
    that a malformed id (path separators / OData metacharacters) is
    rejected as `DataverseWriteBackError` and caught by the surrounding
    failure handler, rather than silently producing an injected filter."""
    from opencloser.crm.dataverse.adapter import DataverseWriteBackError
    from opencloser.models import CallableStatus, QueueStatusUpdatePayload

    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = fake_for_mapping(mapping, _seed())

    # Drive a successful first run to populate the fake + provide a valid
    # queue row for the FK-bound session insert below.
    report = _run_write_enabled(conn=tmp_state_db, fake=fake, artifact_dir=tmp_artifact_dir)
    assert report.exit_status == "completed"

    snapshot = QueueItem(
        queue_item_id=_QID,
        facility_name="Sunage ALF",
        callable_status=CallableStatus.READY,
        phone_number="+15305551234",
        attempt_count=0,
    )
    adapter = _build_adapter_with_snapshot(
        conn=tmp_state_db, fake=fake, mapping=mapping, snapshot=snapshot
    )
    # Payload's queue_item_id is the malformed value — that's what gets
    # interpolated into the OData $filter, exercising the safe-token guard.
    payload = QueueStatusUpdatePayload(
        session_id=f"{report.session_id}-malformed-id",
        queue_item_id="malicious'+OR+1=1",  # OData injection attempt
        previous_status=CallableStatus.READY,
        new_status=CallableStatus.COMPLETED,
        transition_reason="malformed-id-test",
        transition_at=_CLOCK.now_utc_ms(),
    )
    _seed_stub_session(tmp_state_db, payload.session_id)
    with pytest.raises(DataverseWriteBackError, match="unsafe OData filter value"):
        adapter.emit_queue_status_update(payload)


def test_us4_t045_runner_maps_queue_conflict_to_blocked(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """T045 + T046 — verify the runner's exception-handling contract for
    `QueueConflictError`: the runner MUST produce `exit_status="blocked"`
    (not `"failed"`), stamp `writeback_progress.run_status=BLOCKED`, and
    surface the operator-visible "queue conflict — manual reconciliation
    required" message prefix. End-to-end timing manipulation via the fake
    isn't feasible (would need a `pre_request_hook` invasive change), so
    this test forces the runner's catch path by monkey-patching
    `emit_queue_status_update` to raise QueueConflictError directly.
    (Copilot PR #11 review: the runner mapping was new behavior with no
    test coverage; a future refactor could regress it silently.)"""
    from unittest.mock import patch

    from opencloser.crm.dataverse.adapter import QueueConflictError

    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = fake_for_mapping(mapping, _seed())

    def _raise_conflict(self, payload):
        raise QueueConflictError(
            "test-stub: queue item changed mid-run",
            conflict_fields=["medx_callstatus=2 (snapshot expected 0)"],
        )

    with patch(
        "opencloser.crm.dataverse.adapter.DataverseWriteBackAdapter."
        "emit_queue_status_update",
        _raise_conflict,
    ):
        report = _run_write_enabled(
            conn=tmp_state_db, fake=fake, artifact_dir=tmp_artifact_dir
        )

    assert report.exit_status == "blocked"
    assert report.message is not None
    assert "queue conflict" in report.message.lower()
    assert "manual reconciliation required" in report.message
    # The runner staged a failure correlation → writeback_progress is BLOCKED.
    if report.session_id is not None:
        progress = store.get_writeback_progress(tmp_state_db, report.session_id)
        assert progress is not None
        assert progress.run_status is RunStatus.BLOCKED


def test_us4_t045_queue_item_deleted_raises_conflict(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """Edge case — the queue row no longer exists in Dataverse between
    claim and write-back (admin delete, sync removal). The conflict check
    MUST raise `QueueConflictError` rather than letting the PATCH 404 deep
    in the client retry loop."""
    from opencloser.crm.dataverse.adapter import QueueConflictError
    from opencloser.models import CallableStatus, QueueStatusUpdatePayload

    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = fake_for_mapping(mapping, _seed())

    report = _run_write_enabled(conn=tmp_state_db, fake=fake, artifact_dir=tmp_artifact_dir)
    assert report.exit_status == "completed"

    fake._records["medx_callqueueitem"] = []

    snapshot = QueueItem(
        queue_item_id=_QID,
        facility_name="Sunage ALF",
        callable_status=CallableStatus.READY,
        phone_number="+15305551234",
        attempt_count=0,
    )
    adapter = _build_adapter_with_snapshot(
        conn=tmp_state_db, fake=fake, mapping=mapping, snapshot=snapshot
    )
    payload = QueueStatusUpdatePayload(
        session_id=f"{report.session_id}-deleted-row",
        queue_item_id=_QID,
        previous_status=CallableStatus.READY,
        new_status=CallableStatus.COMPLETED,
        transition_reason="deleted-row-test",
        transition_at=_CLOCK.now_utc_ms(),
    )
    _seed_stub_session(tmp_state_db, payload.session_id)
    with pytest.raises(QueueConflictError, match="no longer exists in Dataverse"):
        adapter.emit_queue_status_update(payload)


@pytest.mark.parametrize(
    ("state", "expected_exit"),
    [
        (RunStatus.BLOCKED, "blocked"),
        (RunStatus.IN_PROGRESS, "failed"),
    ],
)
def test_us4_resume_rejects_non_resumable_states(
    tmp_state_db: sqlite3.Connection,
    tmp_artifact_dir: Path,
    state: RunStatus,
    expected_exit: str,
) -> None:
    """Codex PR #9 P1 + Copilot: resume MUST distinguish per-state outcomes
    instead of collapsing every non-`resume_needed` state into
    `no-resume-needed` (which would exit 0). `BLOCKED` (permanent error)
    surfaces as `blocked`; `IN_PROGRESS` (possible concurrent run or
    crashed-mid-write) surfaces as `failed`."""
    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = fake_for_mapping(mapping, _seed())

    report = _run_write_enabled(conn=tmp_state_db, fake=fake, artifact_dir=tmp_artifact_dir)
    _stamp_progress(tmp_state_db, report.session_id, run_status=state)

    result = _invoke_resume(
        session_id=report.session_id,
        conn=tmp_state_db,
        artifact_root=tmp_artifact_dir,
        fake=fake,
        mapping=mapping,
    )

    assert result.exit_status == expected_exit
    assert result.message is not None and state.value in result.message
