"""T035 — US2 integration test: rehearsal places zero calls and zero CRM writes.

A rehearsal / readiness invocation (``run_mode = rehearsal``, the default when
``--real-call`` is omitted) verifies readiness and produces planned artifacts
WITHOUT placing a SignalWire call and WITHOUT creating or updating any Dataverse
record (FR-002, SC-002, SC-011). This is the safety net that makes the real-call
run (US1) trustworthy.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from opencloser.crm.dataverse.mapping import load_mapping
from opencloser.models import Slice3RunMode
from tests.fixtures.dataverse.fake import DataverseFake
from tests.fixtures.dataverse.helpers import fake_for_mapping
from tests.fixtures.slice2_configs import seed
from tests.fixtures.slice3_configs import find_run_report, run_real_call

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAPPING_FIXTURE = _REPO_ROOT / "tests/fixtures/dataverse/dataverse_mapping.json"


def _all_mutations(fake: DataverseFake) -> tuple[list, list]:
    """Every Dataverse create + update the fake observed this run."""
    return list(fake.created), list(fake.patched)


def test_us2_rehearsal_places_zero_calls_and_zero_mutations(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """Acceptance (US2 #1): a default (no ``--real-call``) run produces a
    readiness + planned-write-back result while creating or updating ZERO
    Dataverse records and placing ZERO SignalWire calls."""
    fake = fake_for_mapping(load_mapping(_MAPPING_FIXTURE), seed())

    report = run_real_call(
        conn=tmp_state_db,
        fake=fake,
        transport_fixture="connected",
        conversation_fixture="interested_callback_requested",
        artifact_dir=tmp_artifact_dir,
        run_mode=Slice3RunMode.REHEARSAL,
    )

    assert report is not None, "T038 must implement the rehearsal-mode branch of run_one_real_call"
    assert report.run_mode is Slice3RunMode.REHEARSAL

    # Zero Dataverse create OR update operations (SC-002, SC-011). The dry-run
    # adapter CAPTURES every emit_* instead of issuing it, so the fake records
    # nothing.
    created, patched = _all_mutations(fake)
    assert created == [], f"rehearsal MUST create 0 Dataverse records; got {created!r}"
    assert patched == [], f"rehearsal MUST update 0 Dataverse records; got {patched!r}"

    # The run report names the rehearsal mode and leaves the real provider call
    # id not-yet-assigned (no dial occurred).
    run_report = find_run_report(tmp_artifact_dir)
    assert run_report is not None, "rehearsal MUST still write run_report.json (FR-036)"
    assert run_report.get("run_mode") == Slice3RunMode.REHEARSAL.value
    assert run_report.get("real_provider_call_id") is None, (
        "no SignalWire call is placed in rehearsal, so the real provider call id "
        "must be not-yet-assigned (null)"
    )
