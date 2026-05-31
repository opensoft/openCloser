"""T019 — US1 integration test: terminal states `no_answer` / `voicemail` / `failed`.

A real call that never reaches a connected conversation finalizes in the
matching terminal disposition. Per the Slice 1 write-back contract: no false
connected-call Phone Call activity is recorded, no follow-up Task is created,
and the per-disposition queue-status / attempt write-back map is preserved.

Mirrors the Slice 1 SC-006 parametrization in `test_sc006_no_false_activity.py`,
driven through the Slice 3 real-call runner with the SignalWire transport fake.

TDD red (write first): the US1 runner core (T034) is unimplemented, so
`run_real_call` returns `None` and the `report is not None` assertion fails red.
"""

from __future__ import annotations

import json
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

# Dataverse Phone Call activity fields that would assert a *connected* call.
# A terminal (non-connected) outcome MUST NOT populate any of them. These are the
# standard Dynamics phonecall timestamps the Slice 2 adapter emits
# (`adapter._phone_call_body`: `actualstart` / `actualend`, un-prefixed) — the
# Slice 3 `connected_call_timestamps` {answered_at, completed_at} map onto them.
_CONNECTED_MARKERS = ("actualstart", "actualend")


@pytest.mark.parametrize(
    "transport_fixture,expected_disposition",
    [
        ("no_answer", Disposition.NO_ANSWER),
        ("voicemail", Disposition.VOICEMAIL),
        ("failed", Disposition.FAILED),
    ],
)
def test_us1_real_call_terminal_state_no_false_activity(
    tmp_state_db: sqlite3.Connection,
    tmp_artifact_dir: Path,
    transport_fixture: str,
    expected_disposition: Disposition,
) -> None:
    """Acceptance: a non-connected real call records no false connected-call
    activity and no follow-up Task, but still updates the queue write-back map."""
    fake = fake_for_mapping(load_mapping(_MAPPING_FIXTURE), seed())

    report = run_real_call(
        conn=tmp_state_db,
        fake=fake,
        transport_fixture=transport_fixture,
        conversation_fixture=None,
        artifact_dir=tmp_artifact_dir,
    )

    assert report is not None, (
        f"T034 must implement run_one_real_call so a {transport_fixture} run "
        f"produces a RealCallRunReport"
    )
    assert report.final_disposition is expected_disposition

    # No follow-up Task on a terminal disposition (Slice 1 write-back contract).
    assert created_of(fake, "task") == [], (
        f"{transport_fixture} is terminal — no follow-up Task may be created"
    )

    # No false connected-call Phone Call activity: any Phone Call activity that
    # was recorded MUST NOT claim connected-call timestamps / duration.
    for activity in created_of(fake, "phonecall"):
        for marker in _CONNECTED_MARKERS:
            assert not activity.get(marker), (
                f"{transport_fixture} recorded a connected-call marker {marker!r} "
                f"on the Phone Call activity (SC-006 violation): {json.dumps(activity)}"
            )

    # Per-disposition queue write-back map preserved: exactly one queue-status
    # update carries the session stamp. (`medx_lastdisposition` holds the
    # adapter's `transition_reason`, which is not the bare Disposition value, so
    # the session stamp is the stable per-session anchor to assert on here.)
    patches = queue_patches(fake)
    assert len(patches) == 1, "exactly one queue-status update per session"
    assert patches[0].get("medx_lastsessionid") == report.session_id
