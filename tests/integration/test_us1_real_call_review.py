"""T021 — US1 integration test: `needs_human_review` disposition.

A connected real call whose extracted state is uncertain finalizes as
`needs_human_review`. Exactly one review Task is created and assigned to the
configured review owner, carrying a reason code drawn from the Slice 1
enumerated `HumanReviewReason` set.

TDD red (write first): the US1 runner core (T034), CRM Slice 3 extensions
(T031), and run-report builder (T033) are unimplemented, so `run_real_call`
returns `None` and the `report is not None` assertion fails red, naming T034.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from opencloser.crm.dataverse.mapping import load_mapping
from opencloser.models import Disposition, HumanReviewReason
from tests.fixtures.dataverse.helpers import fake_for_mapping
from tests.fixtures.slice2_configs import OWNER_REVIEW, seed
from tests.fixtures.slice3_configs import (
    created_of,
    find_run_report,
    queue_patches,
    run_real_call,
)

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAPPING_FIXTURE = _REPO_ROOT / "tests/fixtures/dataverse/dataverse_mapping.json"

_VALID_REASON_CODES = {r.value for r in HumanReviewReason}


def test_us1_real_call_needs_human_review_routes_review_task(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """Acceptance: an uncertain connected call creates exactly one review Task
    routed to the review owner with an enumerated reason code."""
    fake = fake_for_mapping(load_mapping(_MAPPING_FIXTURE), seed())

    report = run_real_call(
        conn=tmp_state_db,
        fake=fake,
        transport_fixture="connected",
        conversation_fixture="needs_human_review_uncertain_role",
        artifact_dir=tmp_artifact_dir,
    )

    assert report is not None, (
        "T034 must implement run_one_real_call so a needs_human_review run "
        "produces a RealCallRunReport"
    )
    assert report.final_disposition is Disposition.NEEDS_HUMAN_REVIEW

    # Exactly one review Task, routed to the configured review owner (FR-025).
    tasks = created_of(fake, "task")
    assert len(tasks) == 1, "exactly one review Task per needs_human_review session"
    assert tasks[0]["ownerid@odata.bind"] == f"/systemusers({OWNER_REVIEW})", (
        "review Task must be assigned to the configured review owner (FR-025)"
    )

    # Queue-status reflects the blocked/review transition (Slice 1/2 map: status 3).
    patches = queue_patches(fake)
    assert len(patches) == 1, "exactly one queue-status update per session"
    assert patches[0]["medx_callstatus"] == 3

    # The run report carries a reason code from the Slice 1 enumerated set.
    run_report = find_run_report(tmp_artifact_dir)
    assert run_report is not None, "T033 must write run_report.json on every run"
    reason = run_report.get("human_review_reason")
    assert reason in _VALID_REASON_CODES, (
        f"needs_human_review must carry an enumerated HumanReviewReason code; "
        f"got {reason!r}"
    )
