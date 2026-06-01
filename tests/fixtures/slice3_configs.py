"""Shared Slice 3 real-call integration driver + helpers (US1 T017-T021).

Slice 3 reuses the Slice 2 Dataverse write-back surface (extended additively per
T031), so the Dataverse mapping, fake, seed, and owner IDs are identical to
Slice 2. This module wraps :func:`opencloser.slice3.runner.run_one_real_call`
with the fixture wiring every US1 integration test shares, so the five [P]
test files do not each re-duplicate the driver (per the SonarCloud new-code
duplication threshold; same rationale as ``slice2_configs.py``).

The driver is deliberately tolerant of the T034 TDD-red state: until the runner
core is implemented it raises ``NotImplementedError``. :func:`run_real_call`
catches that and returns ``None`` so each test fails on a clear assertion
(``report is not None``) that names T034, rather than erroring at the call site.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from opencloser.core.clock import FrozenClock
from opencloser.crm.dataverse.queue_loader import ExplicitId
from opencloser.models import Slice3RunMode
from tests.fixtures.dataverse.fake import DataverseFake
from tests.fixtures.slice2_configs import (
    QID,
    slice1_config,
    slice2_config,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAPPING_FIXTURE = _REPO_ROOT / "tests/fixtures/dataverse/dataverse_mapping.json"
_CONVERSATIONS = _REPO_ROOT / "tests/fixtures/conversations"
_TRANSPORT_FIXTURES = _REPO_ROOT / "tests/fixtures/transport_events"

# A FrozenClock inside the configured call window for deterministic eligibility,
# matching the Slice 2 integration tests.
CLOCK = FrozenClock(datetime(2026, 5, 22, 19, 0, 0, tzinfo=UTC))

CAMPAIGN_ID = "alf-q2-davis"
OPERATOR_A = "operator-a"


def run_real_call(
    *,
    conn,
    fake: DataverseFake,
    transport_fixture: str,
    conversation_fixture: str | None,
    artifact_dir: Path,
    run_mode: Slice3RunMode = Slice3RunMode.REAL_CALL,
    operator_id: str = OPERATOR_A,
    queue_item_id: str = QID,
):
    """Drive one Slice 3 real-call run through the injectable runner core.

    Returns the :class:`~opencloser.slice3.runner.RealCallRunReport`, or ``None``
    while the T034 runner core is an unimplemented stub (TDD-red).
    """
    from opencloser.slice3.runner import run_one_real_call

    cfg2 = slice2_config(mapping_path=_MAPPING_FIXTURE)
    try:
        return run_one_real_call(
            ExplicitId(queue_item_id),
            transport_fixture=_TRANSPORT_FIXTURES / f"{transport_fixture}.json",
            conversation_fixture=(
                _CONVERSATIONS / f"{conversation_fixture}.json"
                if conversation_fixture
                else None
            ),
            slice1_config=slice1_config(artifact_dir, Path(":memory:")),
            slice2_config=cfg2,
            dataverse_client=fake.client(cfg2.retry),
            conn=conn,
            campaign_id=CAMPAIGN_ID,
            operator_id=operator_id,
            run_mode=run_mode,
            clock=CLOCK,
        )
    except NotImplementedError:
        return None


def find_run_report(artifact_dir: Path) -> dict | None:
    """Locate and parse the most recent ``run_report.json`` under ``artifact_dir``.

    Returns ``None`` if no run report was written (e.g. while the T033 builder
    and T034 runner are unimplemented).
    """
    candidates = list(artifact_dir.rglob("run_report.json"))
    if not candidates:
        return None
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return json.loads(latest.read_text(encoding="utf-8"))


def find_planned_writeback(artifact_dir: Path) -> dict | None:
    """Locate and parse ``planned_writeback.json`` under ``artifact_dir`` (US2 T039).

    Returns ``None`` if no rehearsal planned-write-back artifact was written.
    """
    candidates = list(artifact_dir.rglob("planned_writeback.json"))
    if not candidates:
        return None
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return json.loads(latest.read_text(encoding="utf-8"))


def created_of(fake: DataverseFake, entity: str) -> list[dict]:
    """All record bodies POSTed to the Dataverse fake for ``entity``."""
    return [body for ent, body in fake.created if ent == entity]


def queue_patches(fake: DataverseFake) -> list[dict]:
    """All change-sets PATCHed onto the ``medx_callqueueitem`` queue record."""
    return [changes for ent, _id, changes in fake.patched if ent == "medx_callqueueitem"]


# FR-036 (Round 2-amended) required run-report field set — kept in sync with the
# T016 CLI contract test (`tests/contract/test_cli_slice3.py`) and the
# `opencloser.models.RunReport` model.
REQUIRED_RUN_REPORT_FIELDS: tuple[str, ...] = (
    "run_mode",
    "session_id",
    "operator_identity",
    "real_provider_call_id",
    "persona_version",
    "runtime_identity",
    "final_disposition",
    "per_writeback_operation_status",
    "shadow_stt",
    "telephony_readiness_summary",
    "callbacks_audit_row_count",
    "conflicting_callbacks_audit_row_count",
    "rejected_auth_callbacks_count",
    "started_at",
)
