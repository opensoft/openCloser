"""T042 — US3 integration test: E.164 hard pre-dial block (FR-010).

A missing / blank / malformed destination phone number blocks before any
SignalWire dial: exit code 4, no call placed, no attempt consumed, no Phone Call
activity. Slice 3 promotes the Slice 2 non-E.164 data-quality warning to a hard
pre-dial block.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from opencloser.crm.dataverse.mapping import load_mapping
from opencloser.slice3.runner import EXIT_TELEPHONY_READINESS_FAILURE
from tests.fixtures.dataverse.helpers import fake_for_mapping
from tests.fixtures.slice2_configs import seed
from tests.fixtures.slice3_configs import (
    created_of,
    find_telephony_readiness,
    run_real_call,
)

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAPPING_FIXTURE = _REPO_ROOT / "tests/fixtures/dataverse/dataverse_mapping.json"


@pytest.mark.parametrize("bad_phone", ["", "not-a-phone", "5305551234", "+1 530 555 1234"])
def test_us3_non_e164_phone_blocks_before_dial(
    bad_phone: str,
    tmp_state_db: sqlite3.Connection,
    tmp_artifact_dir: Path,
) -> None:
    """A non-E.164 destination phone exits 4 before dial with zero side effects."""
    fake = fake_for_mapping(load_mapping(_MAPPING_FIXTURE), seed(phone=bad_phone))

    report = run_real_call(
        conn=tmp_state_db,
        fake=fake,
        transport_fixture="connected",
        conversation_fixture="interested_callback_requested",
        artifact_dir=tmp_artifact_dir,
    )

    assert report is not None
    assert report.exit_code == EXIT_TELEPHONY_READINESS_FAILURE, (
        f"non-E.164 phone {bad_phone!r} must exit {EXIT_TELEPHONY_READINESS_FAILURE} (FR-010)"
    )

    # No Phone Call activity, no attempt, no Dataverse mutation.
    assert created_of(fake, "phonecall") == [], "no Phone Call activity for a blocked dial"
    assert list(fake.created) == [] and list(fake.patched) == []

    readiness = find_telephony_readiness(tmp_artifact_dir)
    assert readiness is not None
    failed = {c["check_name"] for c in readiness["checks"] if c["result"] == "fail"}
    assert "destination_phone_e164" in failed, (
        f"the destination_phone_e164 check must fail for {bad_phone!r}; failed={sorted(failed)}"
    )
