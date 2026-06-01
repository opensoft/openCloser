"""T041 — US3 integration test: per-readiness-category exit-before-dial.

For each telephony FR-009 readiness category, a real-call run exits before any
SignalWire dial with exit code 4, names the failing check in
``telephony_readiness.json``, places zero SignalWire calls, consumes zero
attempts, and creates / updates zero Dataverse records (FR-009 - FR-011).

The Dataverse-metadata category is gated upstream (exit 7) and the eligibility
category resolves to a blocked disposition (exit 0); both are covered by their
own tests. The destination-phone E.164 category is covered by ``test_us3_e164_block``.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from opencloser.crm.dataverse.mapping import load_mapping
from opencloser.slice3.readiness import Slice3TelephonyConfig
from opencloser.slice3.runner import EXIT_TELEPHONY_READINESS_FAILURE
from tests.fixtures.dataverse.helpers import fake_for_mapping
from tests.fixtures.slice2_configs import seed
from tests.fixtures.slice3_configs import (
    find_telephony_readiness,
    run_real_call,
)

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAPPING_FIXTURE = _REPO_ROOT / "tests/fixtures/dataverse/dataverse_mapping.json"

# (label, telephony-config override, expected failing check_name) for the six
# telephony FR-009 checks whose failure exits with code 4.
_CATEGORIES = [
    ("signalwire_credentials", {"signalwire_credentials_present": False}, "signalwire_credentials"),
    ("source_caller_id", {"source_caller_id": None}, "source_caller_id_authorized"),
    (
        "status_callback_url",
        {"status_callback_url_template": None},
        "status_callback_url_configured",
    ),
    ("media_callback_url", {"media_callback_url_template": None}, "media_callback_url_configured"),
    (
        "persona_runtime_mapping",
        {"campaign_persona_runtime_mapping_present": False},
        "campaign_persona_runtime_mapping",
    ),
    ("task_owner_mapping", {"task_owner_mapping_present": False}, "task_owner_mapping_resolved"),
]


@pytest.mark.parametrize(
    ("label", "override", "expected_check"), _CATEGORIES, ids=[c[0] for c in _CATEGORIES]
)
def test_us3_readiness_category_exits_before_dial(
    label: str,
    override: dict,
    expected_check: str,
    tmp_state_db: sqlite3.Connection,
    tmp_artifact_dir: Path,
) -> None:
    """Each telephony readiness failure exits 4, names the failing check, and
    places zero calls / mutations / attempts."""
    fake = fake_for_mapping(load_mapping(_MAPPING_FIXTURE), seed())

    report = run_real_call(
        conn=tmp_state_db,
        fake=fake,
        transport_fixture="connected",
        conversation_fixture="interested_callback_requested",
        artifact_dir=tmp_artifact_dir,
        telephony_config=Slice3TelephonyConfig(**override),
    )

    assert report is not None, "T045/T046 must implement the readiness gate"
    assert report.exit_code == EXIT_TELEPHONY_READINESS_FAILURE, (
        f"{label}: a telephony readiness failure must exit "
        f"{EXIT_TELEPHONY_READINESS_FAILURE}; got {report.exit_code}"
    )

    # Zero dial, zero Dataverse mutations, zero attempts (FR-011).
    assert list(fake.created) == [], f"{label}: readiness failure must create 0 Dataverse records"
    assert list(fake.patched) == [], f"{label}: readiness failure must update 0 Dataverse records"

    # The failing check is named in telephony_readiness.json with result=fail.
    readiness = find_telephony_readiness(tmp_artifact_dir)
    assert readiness is not None, "T046 must write telephony_readiness.json on a readiness failure"
    failed = {c["check_name"]: c for c in readiness["checks"] if c["result"] == "fail"}
    assert expected_check in failed, (
        f"{label}: the failing check {expected_check!r} must be named as fail in the readiness "
        f"report; failed checks were {sorted(failed)}"
    )
    assert failed[expected_check]["detail"], "a failed check must carry a human-readable detail"
