"""T020 — US1 integration test: `do_not_call` disposition.

A connected real call where the caller clearly opts out finalizes as
`do_not_call`. The DNC / opt-out + queue-status fields are updated, and — per
Round 2 Q14 — the DNC field write is FIRST in the write-back sequence so a
partial failure can never leave the contact callable. No callback or review
Task is created (FR-024).

TDD red (write first): the US1 runner core (T034), CRM Slice 3 DNC-first
ordering (T031), and run-report builder (T033) are unimplemented, so
`run_real_call` returns `None` and the `report is not None` assertion fails red.
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


def test_us1_real_call_do_not_call_dnc_first(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """Acceptance: a clear opt-out sets DNC first, updates queue-status, and
    emits no callback or review Task."""
    fake = fake_for_mapping(load_mapping(_MAPPING_FIXTURE), seed())

    report = run_real_call(
        conn=tmp_state_db,
        fake=fake,
        transport_fixture="connected",
        conversation_fixture="do_not_call_mid_call",
        artifact_dir=tmp_artifact_dir,
    )

    assert report is not None, (
        "T034 must implement run_one_real_call so a do_not_call run produces a "
        "RealCallRunReport"
    )
    assert report.final_disposition is Disposition.DO_NOT_CALL

    # No callback or review Task on do_not_call (FR-024).
    assert created_of(fake, "task") == [], "do_not_call MUST NOT emit any Task (FR-024)"

    # DNC / opt-out + queue-status fields updated.
    patches = queue_patches(fake)
    assert len(patches) == 1, "exactly one queue-status update per session"
    assert patches[0]["medx_donotcall"] is True
    assert patches[0]["medx_callstatus"] == 4, "do_not_call sets queue status `dnc`"

    # Round 2 Q14: the DNC field write is FIRST in the write-back sequence. The
    # run report's per_writeback_operation_status[0] reflects the DNC variant.
    run_report = find_run_report(tmp_artifact_dir)
    assert run_report is not None, (
        "T033 must write run_report.json so DNC-first ordering is auditable"
    )
    status_list = run_report.get("per_writeback_operation_status")
    assert isinstance(status_list, list) and status_list, (
        "per_writeback_operation_status must be a non-empty list on do_not_call"
    )
    assert status_list[0].get("operation") == QueueStatusUpdateVariant.DNC.value, (
        f"Round 2 Q14: first write-back operation on do_not_call must be the DNC "
        f"variant; got {status_list[0]!r}"
    )
