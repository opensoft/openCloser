"""T051 — US4: late-after-finalization callbacks are conflicting (FR-027).

A status callback (a second terminal event) arriving after the session is
finalized MUST NOT change the disposition, MUST NOT mutate the normalized
result, MUST NOT increment the attempt count, and MUST NOT emit a new CRM
write-back payload — but MUST be recorded in `conflicting_callbacks_audit.jsonl`.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from opencloser.crm.dataverse.mapping import load_mapping
from opencloser.models import Disposition
from tests.fixtures.dataverse.helpers import fake_for_mapping
from tests.fixtures.slice2_configs import seed
from tests.fixtures.slice3_configs import (
    created_of,
    find_jsonl,
    find_run_report,
    queue_patches,
    run_real_call,
)

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAPPING_FIXTURE = _REPO_ROOT / "tests/fixtures/dataverse/dataverse_mapping.json"


def test_us4_late_failed_after_completed_is_conflicting(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """connected → completed → late `failed`: disposition unchanged; the late
    callback lands in the conflicting log, not in the write-back."""
    fake = fake_for_mapping(load_mapping(_MAPPING_FIXTURE), seed())

    report = run_real_call(
        conn=tmp_state_db,
        fake=fake,
        transport_fixture="conflicting_failed_after_completed",
        conversation_fixture="interested_callback_requested",
        artifact_dir=tmp_artifact_dir,
    )

    assert report is not None
    # The late `failed` did NOT flip the finalized connected-call disposition.
    assert report.final_disposition is Disposition.INTERESTED_CALLBACK_REQUESTED
    assert len(created_of(fake, "phonecall")) == 1
    assert len(queue_patches(fake)) == 1, "the late callback emits no new write-back payload"

    conflicting = find_jsonl(tmp_artifact_dir, "conflicting_callbacks_audit.jsonl")
    assert len(conflicting) == 1, "the late `failed` callback is recorded as conflicting"
    assert conflicting[0]["would_have_been"] == "failed"
    assert (
        conflicting[0]["finalized_disposition"] == Disposition.INTERESTED_CALLBACK_REQUESTED.value
    )

    run_report = find_run_report(tmp_artifact_dir)
    assert run_report is not None
    assert run_report["conflicting_callbacks_audit_row_count"] == 1
