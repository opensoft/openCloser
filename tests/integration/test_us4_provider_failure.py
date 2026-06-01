"""T052 — US4: provider failure / no-answer / voicemail (acceptance scenario #3).

When SignalWire reports a non-connected outcome, the normalized disposition
matches, the Dataverse queue is updated, the attempt count is incremented
exactly once, and NO false connected-call Phone Call activity is created.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from opencloser.crm.dataverse.mapping import load_mapping
from opencloser.models import Disposition
from tests.fixtures.dataverse.helpers import fake_for_mapping
from tests.fixtures.slice2_configs import seed
from tests.fixtures.slice3_configs import created_of, queue_patches, run_real_call

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAPPING_FIXTURE = _REPO_ROOT / "tests/fixtures/dataverse/dataverse_mapping.json"

_CASES = [
    ("failed", Disposition.FAILED),
    ("no_answer", Disposition.NO_ANSWER),
    ("voicemail", Disposition.VOICEMAIL),
]


@pytest.mark.parametrize(("fixture", "expected"), _CASES, ids=[c[0] for c in _CASES])
def test_us4_non_connected_outcome_no_false_activity(
    fixture: str,
    expected: Disposition,
    tmp_state_db: sqlite3.Connection,
    tmp_artifact_dir: Path,
) -> None:
    """A non-connected provider outcome creates no false Phone Call activity and
    updates the queue exactly once."""
    fake = fake_for_mapping(load_mapping(_MAPPING_FIXTURE), seed())

    report = run_real_call(
        conn=tmp_state_db,
        fake=fake,
        transport_fixture=fixture,
        conversation_fixture=None,
        artifact_dir=tmp_artifact_dir,
    )

    assert report is not None
    assert report.final_disposition is expected
    assert created_of(fake, "phonecall") == [], (
        f"{fixture}: a non-connected outcome must create NO Phone Call activity (SC-007)"
    )
    assert created_of(fake, "task") == [], (
        f"{fixture}: no follow-up Task on a non-connected outcome"
    )
    assert len(queue_patches(fake)) == 1, f"{fixture}: exactly one queue-status update"
