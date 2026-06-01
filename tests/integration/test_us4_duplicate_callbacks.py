"""T049 — US4: duplicate status callbacks are idempotent (FR-007/FR-021).

The same `provider_event_id` delivered more than once is a no-op for session
state, the attempt count, and write-back — Dynamics ends with exactly one Phone
Call activity, at most one Task, and one queue-status transition — but every
delivery (including duplicates) is recorded in `callbacks_audit.jsonl`, the
duplicate carrying `is_duplicate=true`.
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


def test_us4_duplicate_callbacks_are_no_ops(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """connected + completed delivered twice → one record set; duplicates logged."""
    fake = fake_for_mapping(load_mapping(_MAPPING_FIXTURE), seed())

    report = run_real_call(
        conn=tmp_state_db,
        fake=fake,
        transport_fixture="duplicate_connected",
        conversation_fixture="interested_callback_requested",
        artifact_dir=tmp_artifact_dir,
    )

    assert report is not None
    assert report.final_disposition is Disposition.INTERESTED_CALLBACK_REQUESTED

    # Exactly one of each Dynamics record despite the duplicate deliveries.
    assert len(created_of(fake, "phonecall")) == 1
    assert len(created_of(fake, "task")) == 1
    assert len(queue_patches(fake)) == 1

    # Every callback (incl. duplicates) is in callbacks_audit.jsonl; the repeats
    # carry is_duplicate=true.
    rows = find_jsonl(tmp_artifact_dir, "callbacks_audit.jsonl")
    assert len(rows) == 4, f"all 4 deliveries recorded; got {len(rows)}"
    dups = [r for r in rows if r["is_duplicate"]]
    assert len(dups) == 2, "the two repeat deliveries are flagged is_duplicate=true"

    # The run report surfaces the callbacks-audit row count.
    run_report = find_run_report(tmp_artifact_dir)
    assert run_report is not None
    assert run_report["callbacks_audit_row_count"] == 4
