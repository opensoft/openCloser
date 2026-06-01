"""T036 — US2 integration test: planned write-back artifacts.

A rehearsal run writes ``planned_writeback.json`` whose payloads match what a
real-call run WOULD have sent to Dataverse (Phone Call activity, queue-status
update, Task when applicable), with the real provider call id marked
not-yet-assigned (US2 acceptance scenario #2). Zero Dataverse writes occur.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from opencloser.crm.dataverse.mapping import load_mapping
from opencloser.models import Disposition, QueueStatusUpdateVariant, Slice3RunMode
from tests.fixtures.dataverse.helpers import fake_for_mapping
from tests.fixtures.slice2_configs import seed
from tests.fixtures.slice3_configs import (
    find_actual_writeback,
    find_planned_writeback,
    find_run_report,
    run_real_call,
)

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAPPING_FIXTURE = _REPO_ROOT / "tests/fixtures/dataverse/dataverse_mapping.json"


def test_us2_planned_writeback_contains_real_call_payloads(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """Acceptance (US2 #2): the planned write-back artifact shows the Phone Call
    activity, queue-status update, and callback Task an ``interested_callback``
    real-call run would have written — with zero Dataverse mutation."""
    fake = fake_for_mapping(load_mapping(_MAPPING_FIXTURE), seed())

    report = run_real_call(
        conn=tmp_state_db,
        fake=fake,
        transport_fixture="connected",
        conversation_fixture="interested_callback_requested",
        artifact_dir=tmp_artifact_dir,
        run_mode=Slice3RunMode.REHEARSAL,
    )

    assert report is not None, "T038 must implement rehearsal mode"
    assert report.final_disposition is Disposition.INTERESTED_CALLBACK_REQUESTED

    # Zero Dataverse writes — the planned artifact is captured, never issued.
    assert list(fake.created) == [] and list(fake.patched) == []

    planned = find_planned_writeback(tmp_artifact_dir)
    assert planned is not None, "T039 must write planned_writeback.json in rehearsal mode"

    # A rehearsal writes ONLY the planned artifact — never actual_writeback.json
    # (that is the real-call counterpart, data-model §4).
    assert find_actual_writeback(tmp_artifact_dir) is None, (
        "rehearsal must NOT write actual_writeback.json"
    )

    # All three planned sub-payloads are present for an interested-callback outcome.
    assert planned.get("phone_call_activity") is not None, (
        "planned write-back must include the Phone Call activity a real call would send"
    )
    assert planned.get("queue_status_update") is not None, (
        "planned write-back must include the queue-status update"
    )
    assert planned.get("task") is not None, (
        "an interested_callback_requested outcome plans exactly one callback Task"
    )

    # The planned queue-status update uses the normal variant (not DNC/blocked).
    assert (
        planned["queue_status_update"].get("variant", QueueStatusUpdateVariant.NORMAL.value)
        in (QueueStatusUpdateVariant.NORMAL.value, None)
        or "variant" not in planned["queue_status_update"]
    )

    # The real provider call id is not-yet-assigned in the run report (no dial),
    # and every planned write-back operation is marked "planned" (not "completed").
    run_report = find_run_report(tmp_artifact_dir)
    assert run_report is not None
    assert run_report.get("real_provider_call_id") is None
    statuses = run_report.get("per_writeback_operation_status") or []
    assert statuses, "per_writeback_operation_status must enumerate the planned operations"
    assert all(s.get("status") == "planned" for s in statuses), (
        f"rehearsal operations must be 'planned', not issued; got {statuses!r}"
    )
