"""T048 — US3 integration test: concurrent-claim exits before dial (Round 1 Q5).

A second invocation observes the queue item as not `ready` (already claimed /
``in_progress`` by another run) and exits with code 3 before any dial — no
attempt consumed, no Phone Call activity, no Task, no Dataverse mutation. The
first invocation is unaffected.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from opencloser.crm.dataverse.mapping import load_mapping
from opencloser.slice3.runner import EXIT_CONCURRENT_CLAIM
from tests.fixtures.dataverse.helpers import fake_for_mapping
from tests.fixtures.slice2_configs import seed
from tests.fixtures.slice3_configs import run_real_call

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAPPING_FIXTURE = _REPO_ROOT / "tests/fixtures/dataverse/dataverse_mapping.json"

# medx_callstatus option-set values (tests/fixtures/dataverse/dataverse_mapping.json):
# 0=ready, 1=in_progress, 2=completed, 3=blocked, 4=dnc.
_IN_PROGRESS = 1


def test_us3_already_claimed_item_exits_3(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """An item already `in_progress` (claimed by another invocation) exits 3
    before dial with zero side effects (Round 1 Q5)."""
    fake = fake_for_mapping(load_mapping(_MAPPING_FIXTURE), seed(status=_IN_PROGRESS))

    report = run_real_call(
        conn=tmp_state_db,
        fake=fake,
        transport_fixture="connected",
        conversation_fixture="interested_callback_requested",
        artifact_dir=tmp_artifact_dir,
    )

    assert report is not None
    assert report.exit_code == EXIT_CONCURRENT_CLAIM, (
        f"an already-claimed (in_progress) item must exit {EXIT_CONCURRENT_CLAIM} "
        f"before dial (Round 1 Q5); got {report.exit_code}"
    )

    # No dial, no Dataverse mutation, no attempt consumed.
    assert list(fake.created) == [], "concurrent-claim block creates 0 Dataverse records"
    assert list(fake.patched) == [], "concurrent-claim block updates 0 Dataverse records"
    assert report.warnings, "the blocked-by-claim exit surfaces an operator-visible message"
