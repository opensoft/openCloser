"""T018 — US1 integration test: `interested_email_captured`.

A connected real call where the caller is interested and volunteers an email
(no callback requested) produces exactly one follow-up Task carrying the
captured email, and updates the queue-status / attempt fields per the Slice 1
write-back contract.

TDD red (write first): the US1 runner core (T034) + CRM Slice 3 extensions
(T031) + run-report builder (T033) are unimplemented, so `run_real_call`
returns `None` and the `report is not None` assertion fails red, naming T034.
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

# The email scripted into tests/fixtures/conversations/interested_email_captured.json.
_CAPTURED_EMAIL = "director@sunset.example.com"


def test_us1_real_call_email_captured_single_followup_task(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """Acceptance: an interested caller who volunteers an email gets exactly one
    follow-up Task with that email; queue-status moves to `completed`."""
    fake = fake_for_mapping(load_mapping(_MAPPING_FIXTURE), seed())

    report = run_real_call(
        conn=tmp_state_db,
        fake=fake,
        transport_fixture="connected",
        conversation_fixture="interested_email_captured",
        artifact_dir=tmp_artifact_dir,
    )

    assert report is not None, (
        "T034 must implement run_one_real_call so an email-captured run produces "
        "a RealCallRunReport"
    )
    assert report.final_disposition is Disposition.INTERESTED_EMAIL_CAPTURED

    # Exactly one follow-up Task, and it carries the captured email.
    tasks = created_of(fake, "task")
    assert len(tasks) == 1, "exactly one follow-up Task per email-captured session"
    assert _CAPTURED_EMAIL in json.dumps(tasks[0]), (
        "the follow-up Task payload must carry the captured email (FR-018 Slice 1 contract)"
    )

    # Queue-status / attempt updated per the Slice 1 write-back contract: an
    # email-captured outcome marks the queue item `completed` (medx_callstatus == 2).
    patches = queue_patches(fake)
    assert len(patches) == 1, "exactly one queue-status update per session"
    assert patches[0]["medx_callstatus"] == 2, "email-captured outcome marks queue `completed`"
    assert patches[0].get("medx_lastsessionid") == report.session_id
