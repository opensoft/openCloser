"""T050 — US4: out-of-order callbacks normalize to a coherent disposition.

`completed` arriving before `connected` (delivery anomaly) must still produce a
single coherent disposition consistent with the actual outcome — the
orchestrator MUST NOT rely on strict ordering — and the out-of-order delivery is
recorded for audit.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from opencloser.crm.dataverse.mapping import load_mapping
from opencloser.models import Disposition
from tests.fixtures.dataverse.helpers import fake_for_mapping
from tests.fixtures.slice2_configs import seed
from tests.fixtures.slice3_configs import created_of, find_jsonl, run_real_call

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAPPING_FIXTURE = _REPO_ROOT / "tests/fixtures/dataverse/dataverse_mapping.json"


def test_us4_out_of_order_yields_coherent_disposition(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """completed-before-connected still resolves to the connected-call outcome."""
    fake = fake_for_mapping(load_mapping(_MAPPING_FIXTURE), seed())

    report = run_real_call(
        conn=tmp_state_db,
        fake=fake,
        transport_fixture="out_of_order_completed_first",
        conversation_fixture="interested_callback_requested",
        artifact_dir=tmp_artifact_dir,
    )

    assert report is not None
    # The call connected and completed (just delivered out of order) — the
    # disposition is the connected-call persona outcome, not a failure.
    assert report.final_disposition is Disposition.INTERESTED_CALLBACK_REQUESTED
    assert len(created_of(fake, "phonecall")) == 1, "one connected-call Phone Call activity"

    # The out-of-order delivery is recorded in the callbacks audit log.
    rows = find_jsonl(tmp_artifact_dir, "callbacks_audit.jsonl")
    assert any(r["is_out_of_order"] for r in rows), (
        "the late-arriving connection event must be flagged is_out_of_order"
    )
