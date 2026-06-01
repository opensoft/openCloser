"""T017 — US1 integration test: `interested_callback_requested` happy path.

Full-stack Slice 3 real-call run with fixture-driven fakes for SignalWire /
Pipecat / real-time AI plus the in-process Dataverse fake. One eligible queue
item moves from `ready` to `interested_callback_requested`; the run produces a
Phone Call activity, a queue-status update, and a callback Task in Dataverse,
and an `artifacts/<session_id>/run_report.json` carrying every FR-036 field.

TDD red (write first): the US1 runner core `run_one_real_call` (T034), the CRM
Slice 3 extensions (T031), the runtime (T030), the artifact writers (T032), and
the run-report builder (T033) are unimplemented, so `run_real_call` returns
`None` and the `report is not None` assertion fails red, naming T034.

Mirrors the Slice 2 happy-path assertions in `test_us1_write_enabled.py`.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from opencloser.crm.dataverse.mapping import load_mapping
from opencloser.models import Disposition
from tests.fixtures.dataverse.helpers import fake_for_mapping
from tests.fixtures.slice2_configs import OWNER_CALLBACK, seed
from tests.fixtures.slice3_configs import (
    REQUIRED_RUN_REPORT_FIELDS,
    created_of,
    find_actual_writeback,
    find_run_report,
    queue_patches,
    run_real_call,
)

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAPPING_FIXTURE = _REPO_ROOT / "tests/fixtures/dataverse/dataverse_mapping.json"


def test_us1_real_call_callback_full_loop(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """Acceptance: a connected real call with an interested caller requesting a
    callback writes the full Dynamics record set and a complete run report."""
    fake = fake_for_mapping(load_mapping(_MAPPING_FIXTURE), seed())

    report = run_real_call(
        conn=tmp_state_db,
        fake=fake,
        transport_fixture="connected",
        conversation_fixture="interested_callback_requested",
        artifact_dir=tmp_artifact_dir,
    )

    assert report is not None, (
        "T034 must implement run_one_real_call so a connected interested-callback "
        "run produces a RealCallRunReport"
    )
    assert report.final_disposition is Disposition.INTERESTED_CALLBACK_REQUESTED
    assert report.session_id is not None

    # Dataverse fake: exactly one Phone Call activity + one callback Task + one
    # queue-status PATCH (FR-006 / FR-020 / FR-025).
    phonecalls = created_of(fake, "phonecall")
    tasks = created_of(fake, "task")
    patches = queue_patches(fake)
    assert len(phonecalls) == 1, "exactly one Phone Call activity per connected session"
    assert len(tasks) == 1, "exactly one callback Task per interested-callback session"
    assert len(patches) == 1, "exactly one queue-status update per session"

    # Callback Task is routed to the configured callback owner (FR-025).
    assert tasks[0]["ownerid@odata.bind"] == f"/systemusers({OWNER_CALLBACK})"

    # run_report.json contains every FR-036 field.
    run_report = find_run_report(tmp_artifact_dir)
    assert run_report is not None, (
        "T033 must write artifacts/<session_id>/run_report.json on every run"
    )
    missing = [f for f in REQUIRED_RUN_REPORT_FIELDS if f not in run_report]
    assert not missing, f"run_report.json missing FR-036 fields: {missing}"
    assert run_report["final_disposition"] == Disposition.INTERESTED_CALLBACK_REQUESTED.value

    # Phone Call activity carries the real SignalWire SID (FR-006 / FR-020). The
    # data-model pins this at the payload level (`provider_call_id`) and surfaces
    # it in the run report as `real_provider_call_id`; the Dynamics logical field
    # name is chosen by T031, so assert the SID *value* appears in the payload
    # rather than guessing the field name.
    real_sid = run_report.get("real_provider_call_id")
    assert real_sid, "a connected real call must record the SignalWire SID (FR-020)"
    assert real_sid in json.dumps(phonecalls[0]), (
        "Phone Call activity must carry the real SignalWire provider call id (FR-020)"
    )

    # A real-call run emits actual_writeback.json (data-model §4) recording the
    # write-back payloads that WERE issued — the real-call counterpart of the
    # rehearsal planned_writeback.json.
    actual = find_actual_writeback(tmp_artifact_dir)
    assert actual is not None, "a real-call run must write actual_writeback.json (data-model §4)"
    assert actual.get("phone_call_activity") is not None
    assert actual.get("queue_status_update") is not None
    assert actual.get("task") is not None, "interested_callback_requested emits a callback Task"
