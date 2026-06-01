"""T037 — US2 integration test: readiness / eligibility failures surface.

A rehearsal must not silently pass when a pre-dial gate fails: the gap is
surfaced in the run report so an operator finds it BEFORE a real-call run
(US2 acceptance scenario #3). Here the gate is the Slice 1 DNC eligibility rule
(a do-not-call queue item) — the rehearsal surfaces ``disposition = blocked``
with the failing rule named, and still mutates zero Dataverse records.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from opencloser.crm.dataverse.mapping import load_mapping
from opencloser.models import Disposition, Slice3RunMode
from tests.fixtures.dataverse.helpers import fake_for_mapping
from tests.fixtures.slice2_configs import seed
from tests.fixtures.slice3_configs import find_run_report, run_real_call

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAPPING_FIXTURE = _REPO_ROOT / "tests/fixtures/dataverse/dataverse_mapping.json"


def test_us2_rehearsal_surfaces_eligibility_block(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """Acceptance (US2 #3): a rehearsal over an ineligible (DNC) queue item does
    NOT silently pass — it surfaces the block in the run report and still creates
    or updates zero Dataverse records."""
    # A do-not-call queue item: the Slice 1 DNC eligibility rule blocks before dial.
    fake = fake_for_mapping(load_mapping(_MAPPING_FIXTURE), seed(dnc=True))

    report = run_real_call(
        conn=tmp_state_db,
        fake=fake,
        transport_fixture="connected",
        conversation_fixture="interested_callback_requested",
        artifact_dir=tmp_artifact_dir,
        run_mode=Slice3RunMode.REHEARSAL,
    )

    assert report is not None, "T038 must implement rehearsal mode"

    # The gap is surfaced, not silently swallowed: the rehearsal reports a blocked
    # disposition with a non-empty blocked reason.
    assert report.final_disposition is Disposition.BLOCKED, (
        "a rehearsal over an ineligible item must surface the block, not a clean pass"
    )

    run_report = find_run_report(tmp_artifact_dir)
    assert run_report is not None, "rehearsal must still write run_report.json"
    assert run_report.get("final_disposition") == Disposition.BLOCKED.value
    assert run_report.get("blocked_reason"), (
        "the blocked reason (the failing eligibility rule) must be named in the run report"
    )

    # Even on the blocked path, rehearsal mutates zero Dataverse records.
    assert list(fake.created) == [], "blocked rehearsal MUST create 0 Dataverse records"
    assert list(fake.patched) == [], "blocked rehearsal MUST update 0 Dataverse records"
