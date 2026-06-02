"""T060 — US5 integration: clear opt-out → ``do_not_call`` (FR-024).

US5 acceptance scenario #3: when the caller clearly opts out on the live call,
the persona observes the Slice 1 DNC trigger and finalizes ``do_not_call``. The
Dataverse DNC / opt-out + queue-status fields are updated (DNC field FIRST per
Round 2 Q14) and NO callback or review Task is created. The live model has no
authority to soften the opt-out — the deterministic Slice 1 rules own it.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from opencloser.crm.dataverse.mapping import load_mapping
from opencloser.models import Disposition, QueueStatusUpdateVariant
from tests.fixtures.dataverse.helpers import fake_for_mapping
from tests.fixtures.slice2_configs import seed
from tests.fixtures.slice3_configs import (
    created_of,
    find_run_report,
    queue_patches,
    run_real_call,
)

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAPPING_FIXTURE = _REPO_ROOT / "tests/fixtures/dataverse/dataverse_mapping.json"


def test_us5_live_opt_out_finalizes_do_not_call(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    fake = fake_for_mapping(load_mapping(_MAPPING_FIXTURE), seed())

    report = run_real_call(
        conn=tmp_state_db,
        fake=fake,
        transport_fixture="connected",
        conversation_fixture="do_not_call_mid_call",
        artifact_dir=tmp_artifact_dir,
    )

    assert report is not None
    assert report.final_disposition is Disposition.DO_NOT_CALL

    # No callback or review Task on do_not_call (FR-024).
    assert created_of(fake, "task") == [], "do_not_call MUST NOT emit any Task (FR-024)"

    # DNC / opt-out + queue-status fields updated.
    patches = queue_patches(fake)
    assert len(patches) == 1, "exactly one queue-status update per session"
    assert patches[0]["medx_donotcall"] is True
    assert patches[0]["medx_callstatus"] == 4, "do_not_call sets queue status `dnc`"

    # Round 2 Q14: the DNC field write is FIRST in the write-back sequence.
    run_report = find_run_report(tmp_artifact_dir)
    assert run_report is not None
    status_list = run_report.get("per_writeback_operation_status")
    assert isinstance(status_list, list) and status_list
    assert status_list[0].get("operation") == QueueStatusUpdateVariant.DNC.value, (
        "Round 2 Q14: first write-back operation on do_not_call must be the DNC variant"
    )
