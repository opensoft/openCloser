"""T053 — US4: answered-but-no-terminal → live-call abandonment (FR-026 / Q6).

A call placed and acknowledged (connected) that never receives a normalized
terminal event is a live-call abandonment: finalized as `failed` with reason
`live_call_abandonment`, exit code 6, the queue does NOT remain `in_progress`,
and no false connected-call Phone Call activity is created.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from opencloser.crm.dataverse.mapping import load_mapping
from opencloser.models import Disposition
from opencloser.slice3.runner import EXIT_LIVE_CALL_ABANDONMENT
from tests.fixtures.dataverse.helpers import fake_for_mapping
from tests.fixtures.slice2_configs import seed
from tests.fixtures.slice3_configs import created_of, find_run_report, run_real_call

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAPPING_FIXTURE = _REPO_ROOT / "tests/fixtures/dataverse/dataverse_mapping.json"


def test_us4_answered_but_no_terminal_is_abandonment(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """connected with no terminal event finalizes as failed/live_call_abandonment."""
    fake = fake_for_mapping(load_mapping(_MAPPING_FIXTURE), seed())

    report = run_real_call(
        conn=tmp_state_db,
        fake=fake,
        transport_fixture="connected_no_terminal",
        conversation_fixture="interested_callback_requested",
        artifact_dir=tmp_artifact_dir,
    )

    assert report is not None
    assert report.final_disposition is Disposition.FAILED
    assert report.exit_code == EXIT_LIVE_CALL_ABANDONMENT, (
        f"abandonment must exit {EXIT_LIVE_CALL_ABANDONMENT} (FR-026); got {report.exit_code}"
    )

    # No false connected-call Phone Call activity (the call never reached a
    # normalized connected/terminal outcome).
    assert created_of(fake, "phonecall") == [], "abandonment creates no connected-call activity"

    run_report = find_run_report(tmp_artifact_dir)
    assert run_report is not None
    assert run_report["final_disposition"] == Disposition.FAILED.value
    assert run_report.get("blocked_reason") == "live_call_abandonment"
