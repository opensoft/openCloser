"""T043 — US3 integration test: provider-rejected dial (FR-012).

A SignalWire 4xx before placement exits with code 5: no attempt consumed, no
Phone Call activity created; the queue-status is advanced via the dial-blocked
variant per the per-disposition mapping for blocked / failed cases.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from opencloser.crm.dataverse.mapping import load_mapping
from opencloser.slice3.runner import EXIT_PROVIDER_REJECTED_DIAL
from tests.fixtures.dataverse.helpers import fake_for_mapping
from tests.fixtures.slice2_configs import seed
from tests.fixtures.slice3_configs import created_of, find_run_report, run_real_call

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAPPING_FIXTURE = _REPO_ROOT / "tests/fixtures/dataverse/dataverse_mapping.json"


def test_us3_provider_rejected_dial_exits_5(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """A provider 4xx on dial exits 5, consumes no attempt, creates no Phone Call
    activity, and records the dial-blocked queue-status variant."""
    fake = fake_for_mapping(load_mapping(_MAPPING_FIXTURE), seed())

    report = run_real_call(
        conn=tmp_state_db,
        fake=fake,
        transport_fixture="provider_rejected_400",
        conversation_fixture=None,
        artifact_dir=tmp_artifact_dir,
    )

    assert report is not None
    assert report.exit_code == EXIT_PROVIDER_REJECTED_DIAL, (
        f"a provider 4xx on dial must exit {EXIT_PROVIDER_REJECTED_DIAL} (FR-012); "
        f"got {report.exit_code}"
    )

    # No attempt consumed, no Phone Call activity.
    assert created_of(fake, "phonecall") == [], (
        "provider-rejected dial creates no Phone Call activity"
    )
    assert created_of(fake, "task") == [], "provider-rejected dial creates no Task"

    # The dial-blocked queue-status variant is reflected in the run report.
    run_report = find_run_report(tmp_artifact_dir)
    assert run_report is not None
    ops = [s["operation"] for s in run_report.get("per_writeback_operation_status", [])]
    assert "queue_status_update.dial_blocked" in ops, (
        f"provider-rejected dial must record the dial-blocked variant; got {ops}"
    )
    assert "provider_rejected_dial" in (run_report.get("blocked_reason") or ""), (
        "the blocked reason must name the provider-rejected-dial cause"
    )
