"""T044 — US3 integration test: real-call flag absence runs rehearsal (SC-011).

An invocation without the real-call / write-enabled flag runs in rehearsal mode
100% of the time: zero SignalWire calls, zero Dataverse mutations, exit 0 — even
when a telephony readiness check would otherwise fail a real-call run. Rehearsal
surfaces the gap in the readiness report rather than placing a call.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from opencloser.crm.dataverse.mapping import load_mapping
from opencloser.models import Slice3RunMode
from opencloser.slice3.readiness import Slice3TelephonyConfig
from opencloser.slice3.runner import EXIT_SUCCESS
from tests.fixtures.dataverse.helpers import fake_for_mapping
from tests.fixtures.slice2_configs import seed
from tests.fixtures.slice3_configs import find_run_report, run_real_call

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAPPING_FIXTURE = _REPO_ROOT / "tests/fixtures/dataverse/dataverse_mapping.json"


def test_us3_flag_absent_runs_rehearsal_even_when_readiness_would_fail(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """No --real-call flag → rehearsal: exit 0, zero calls, zero mutations, even
    with a broken telephony config that would fail a real-call readiness gate."""
    fake = fake_for_mapping(load_mapping(_MAPPING_FIXTURE), seed())

    report = run_real_call(
        conn=tmp_state_db,
        fake=fake,
        transport_fixture="connected",
        conversation_fixture="interested_callback_requested",
        artifact_dir=tmp_artifact_dir,
        run_mode=Slice3RunMode.REHEARSAL,
        telephony_config=Slice3TelephonyConfig(signalwire_credentials_present=False),
    )

    assert report is not None
    assert report.run_mode is Slice3RunMode.REHEARSAL
    assert report.exit_code == EXIT_SUCCESS, (
        "rehearsal must exit 0 even when a readiness check fails (the gap is surfaced, "
        "not turned into a real-call exit 4)"
    )

    # SC-011: zero SignalWire calls, zero Dataverse mutations.
    assert list(fake.created) == [] and list(fake.patched) == []

    run_report = find_run_report(tmp_artifact_dir)
    assert run_report is not None
    assert run_report.get("run_mode") == Slice3RunMode.REHEARSAL.value
    # The readiness gap is still surfaced in the report (does not silently pass).
    failed = {
        c["check_name"]
        for c in run_report.get("telephony_readiness_summary", [])
        if c["result"] == "fail"
    }
    assert "signalwire_credentials" in failed, "rehearsal must surface the readiness gap"
