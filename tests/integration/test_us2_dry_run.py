"""US2 — Rehearse the run in dry-run mode with zero CRM writes.

End-to-end integration tests that exercise the FR-031 dry-run path against the
in-process Dataverse fake. The dry-run path:

- validates the local mapping artifact but does NOT call live `verify()` (FR-007
  "for the selected run mode" — spec §Edge Cases "Dry-run requested but write
  credentials are absent");
- runs the same Slice 1 orchestrator loop (FR-014 — eligibility, transport,
  persona) so the produced session-result + planned write-back match what a
  write-enabled run would emit;
- routes every `emit_*` through `DataverseWriteBackAdapter` constructed with
  `dry_run=True` so zero POST / PATCH operations reach Dataverse for
  write-back (FR-031, SC-002, SC-013) — Note: the runner still issues GETs
  to load the queue item from Dataverse via `DataverseQueueLoader`; the
  "zero writes" guarantee is scoped to write-back, not all I/O;
- writes the FR-031 dry-run marker alongside the orchestrator's session
  artifacts so an inspector can tell the session was a rehearsal (SC-002).

Covered scenarios:

- happy path (interested_callback_requested) — SC-002, SC-013
- incomplete mapping surfaces the gap — SC-002, US2 §AC3
- dry-run skips live `verify()` even when it would fail in write-enabled mode
  (mode-aware readiness from spec §Edge Cases) — verifies that the same
  inputs that would block a write-enabled run still succeed in dry-run.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from opencloser.core.clock import FrozenClock
from opencloser.crm.dataverse.client import DataverseClient
from opencloser.crm.dataverse.mapping import load_mapping
from opencloser.crm.dataverse.queue_loader import ExplicitId
from opencloser.models import Disposition, RetryConfig, RunMode, Slice2Config
from opencloser.slice2.runner import run_one_crm_item
from tests.fixtures.dataverse.helpers import fake_for_mapping
from tests.fixtures.slice2_configs import (
    OWNER_CALLBACK as _OWNER_CALLBACK,
)
from tests.fixtures.slice2_configs import (
    QID as _QID,
)
from tests.fixtures.slice2_configs import (
    seed as _seed,
)
from tests.fixtures.slice2_configs import (
    slice1_config as _slice1_config,
)
from tests.fixtures.slice2_configs import (
    slice2_config as _slice2_config_shared,
)

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAPPING_FIXTURE = _REPO_ROOT / "tests/fixtures/dataverse/dataverse_mapping.json"
_CONVERSATIONS = _REPO_ROOT / "tests/fixtures/conversations"
_TRANSPORT_FIXTURES = _REPO_ROOT / "tests/fixtures/transport_events"

# FrozenClock inside the configured call window for deterministic eligibility.
_CLOCK = FrozenClock(datetime(2026, 5, 22, 19, 0, 0, tzinfo=UTC))


def _slice2_config(mapping_path: Path = _MAPPING_FIXTURE) -> Slice2Config:
    """US2-flavored slice2 config — CLI default per FR-031 is dry-run; mirror
    that here so the config and the explicit run_mode arg below agree."""
    return _slice2_config_shared(mapping_path=mapping_path, default_mode=RunMode.DRY_RUN)


def _run_dry(
    *,
    conn: sqlite3.Connection,
    client,
    transport_fixture: str,
    conversation_fixture: str | None,
    artifact_dir: Path,
    slice2_config: Slice2Config | None = None,
):
    cfg = slice2_config or _slice2_config()
    return run_one_crm_item(
        selector=ExplicitId(_QID),
        transport_fixture=_TRANSPORT_FIXTURES / f"{transport_fixture}.json",
        conversation_fixture=(
            _CONVERSATIONS / f"{conversation_fixture}.json" if conversation_fixture else None
        ),
        slice1_config=_slice1_config(artifact_dir, Path(":memory:")),
        slice2_config=cfg,
        client=client,
        conn=conn,
        clock=_CLOCK,
        run_mode=RunMode.DRY_RUN,
    )


# ---------------------------------------------------------------------------
# SC-002, SC-013 — happy path: dry-run produces planned artifacts with zero writes
# ---------------------------------------------------------------------------


def test_us2_dry_run_produces_planned_artifacts_and_zero_writes(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = fake_for_mapping(mapping, _seed())

    report = _run_dry(
        conn=tmp_state_db,
        client=fake.client(_slice2_config().retry),
        transport_fixture="connected",
        conversation_fixture="interested_callback_requested",
        artifact_dir=tmp_artifact_dir,
    )

    # Exit status + disposition + session id as in write-enabled.
    assert report.exit_status == "completed"
    assert report.final_disposition is Disposition.INTERESTED_CALLBACK_REQUESTED
    assert report.session_id is not None
    assert report.artifact_dir is not None

    # SC-002 / SC-013 — zero create / update operations against Dataverse.
    assert fake.created == [], "dry-run must not POST any record"
    assert fake.patched == [], "dry-run must not PATCH any record"

    # Local audit artifacts: session-result + writeback + task (planned payloads
    # in dry-run; same filenames since the orchestrator is unchanged per FR-014).
    for name in ("session-result.json", "writeback.json", "task.json"):
        assert (report.artifact_dir / name).exists(), f"missing artifact {name}"

    # FR-031 dry-run marker file.
    marker_path = report.artifact_dir / "dry-run-marker.json"
    assert marker_path.exists(), "dry-run marker not written"
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    assert marker["schema_version"] == "slice2-dry-run-marker-v1"
    assert marker["session_id"] == report.session_id
    assert "zero create or update operations" in marker["note"]

    # The captured planned writeback carries the same conceptual content a
    # write-enabled run would have sent.
    writeback = json.loads((report.artifact_dir / "writeback.json").read_text(encoding="utf-8"))
    assert writeback["session_id"] == report.session_id
    assert writeback["phone_call_activity"] is not None
    assert writeback["queue_status_update"] is not None
    assert writeback["task"] is not None
    # Planned task is assigned to the configured default callback owner — dry-run
    # uses the default without live verification (FR-025 verification happens in
    # write-enabled).
    assert writeback["task"]["assigned_to"] == _OWNER_CALLBACK

    # FR-010 + adapter dry-run — no `crm_correlations` rows (no CRM correlation)
    # and no `writeback_progress` row (no resumable state).
    correlations = tmp_state_db.execute(
        "SELECT COUNT(*) FROM crm_correlations WHERE session_id = ?;",
        (report.session_id,),
    ).fetchone()[0]
    assert correlations == 0, "dry-run must not record CRM correlations"
    progress = tmp_state_db.execute(
        "SELECT COUNT(*) FROM writeback_progress WHERE session_id = ?;",
        (report.session_id,),
    ).fetchone()[0]
    assert progress == 0, "dry-run must not record writeback_progress"


# ---------------------------------------------------------------------------
# US2 §AC3 — dry-run surfaces an incomplete mapping (no silent pass)
# ---------------------------------------------------------------------------


def test_us2_dry_run_blocks_when_mapping_missing(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path, tmp_path: Path
) -> None:
    # Point Slice2Config at a mapping artifact that doesn't exist on disk.
    missing_path = tmp_path / "missing-mapping.json"
    cfg = _slice2_config(mapping_path=missing_path)

    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = fake_for_mapping(mapping, _seed())

    report = _run_dry(
        conn=tmp_state_db,
        client=fake.client(cfg.retry),
        transport_fixture="connected",
        conversation_fixture="interested_callback_requested",
        artifact_dir=tmp_artifact_dir,
        slice2_config=cfg,
    )

    # Readiness blocks with an operator-visible message.
    assert report.exit_status == "blocked"
    assert report.message is not None and "mapping artifact" in report.message
    # No artifacts were produced and no Dataverse calls occurred.
    assert fake.created == []
    assert fake.patched == []
    # A readiness block must leave NO partial artifacts on disk — protects
    # against future regressions where readiness fails but a session-result /
    # writeback / dry-run-marker still gets written (Sourcery PR #7 review).
    assert report.artifact_dir is None
    assert (
        not tmp_artifact_dir.exists() or list(tmp_artifact_dir.iterdir()) == []
    ), f"readiness block must not write artifacts; found {list(tmp_artifact_dir.iterdir())}"


# ---------------------------------------------------------------------------
# Spec §Edge Cases "Dry-run requested but write credentials are absent" —
# dry-run readiness skips live `verify()` even when it would fail in write-enabled.
# ---------------------------------------------------------------------------


def _broken_dataverse_client() -> DataverseClient:
    """Build a DataverseClient whose token-acquire raises a DataverseError. Per
    `contracts/metadata-discovery-verification.md` §5 + spec §Edge Cases
    "Dry-run requested but write credentials are absent", dry-run readiness
    MUST tolerate `verify()` failing this way — the placeholder report path
    keeps the run going.

    (Earlier this test asserted that dry-run NEVER touches the client. That
    was wrong per the contract — Copilot PR #7 review pointed this out: the
    contract explicitly says dry-run runs `verify` AND surfaces gaps, with
    the special case that missing write credentials are tolerated.)"""
    from opencloser.crm.dataverse.errors import PermanentDataverseError

    class _BrokenToken:
        def token(self, *, now: float | None = None) -> str:
            raise PermanentDataverseError(
                "OAuth token acquisition failed (test stub — missing creds)",
                status_code=401,
            )

    transport = httpx.MockTransport(
        lambda _request: httpx.Response(401, json={"error": "unauthorized"})
    )

    return DataverseClient(
        "https://broken.crm.dynamics.com",
        _BrokenToken(),
        RetryConfig(max_retries=0, backoff_seconds=[1.0], retry_after_cap_seconds=30.0),
        http=httpx.Client(transport=transport),
        sleep=lambda _seconds: None,
    )


def test_us2_dry_run_readiness_tolerates_verify_connectivity_failure(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """Confirms that dry-run readiness calls live `verify()` (per
    `contracts/metadata-discovery-verification.md` §5) but tolerates
    auth/connectivity failures (the spec §Edge Cases "dry-run + missing write
    credentials" rule). With a working fake the dry-run completes; the
    metadata report is the live one (drift may be populated)."""
    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = fake_for_mapping(mapping, _seed())

    report = _run_dry(
        conn=tmp_state_db,
        client=fake.client(_slice2_config().retry),
        transport_fixture="connected",
        conversation_fixture="interested_callback_requested",
        artifact_dir=tmp_artifact_dir,
    )

    assert report.exit_status == "completed"
    assert report.metadata_report is not None
    assert report.metadata_report.ok is True


def test_us2_dry_run_readiness_continues_when_verify_fails(
    tmp_path: Path,
) -> None:
    """Lower-level proof: invoke `_verify_readiness` directly with a broken
    client whose token-acquire raises `PermanentDataverseError`. Dry-run
    readiness must complete without raising — the `verify()` failure is caught
    and a placeholder report is returned, satisfying the spec §Edge Cases
    "dry-run + missing write credentials" rule."""
    from opencloser.slice2.runner import _ReadinessResult, _verify_readiness

    cfg = _slice2_config()
    broken_client = _broken_dataverse_client()

    result = _verify_readiness(cfg, broken_client, _CLOCK, dry_run=True)

    # The placeholder return path — readiness succeeded despite a 401 from
    # verify(), because the spec edge case tolerates it in dry-run.
    assert isinstance(result, _ReadinessResult)
    assert result.metadata_report.ok is True
    assert result.metadata_report.checked_at == _CLOCK.now_utc_ms()


def test_us2_dry_run_readiness_blocks_on_403_permission_regression(
    tmp_path: Path,
) -> None:
    """Codex PR #7 round-3 P1: dry-run MUST NOT silently treat a 403 from
    `verify()` (e.g. permission regression on `EntityDefinitions` while queue
    reads still work) as success. Only auth-401 and transient failures are
    tolerated; 403/permission failures STILL block dry-run."""
    from opencloser.crm.dataverse.errors import PermanentDataverseError
    from opencloser.slice2.runner import _verify_readiness

    cfg = _slice2_config()

    class _ForbiddenToken:
        def token(self, *, now: float | None = None) -> str:
            raise PermanentDataverseError(
                "EntityDefinitions returned HTTP 403 — test stub for permission regression",
                status_code=403,
            )

    forbidden_client = DataverseClient(
        "https://forbidden.crm.dynamics.com",
        _ForbiddenToken(),
        RetryConfig(max_retries=0, backoff_seconds=[1.0], retry_after_cap_seconds=30.0),
        http=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(403))),
        sleep=lambda _seconds: None,
    )

    result = _verify_readiness(cfg, forbidden_client, _CLOCK, dry_run=True)

    # A 403 is NOT a tolerable verify failure — must surface as a structured
    # blocked report, not a synthetic ok-report.
    from opencloser.slice2.runner import CrmRunReport

    assert isinstance(result, CrmRunReport)
    assert result.exit_status == "blocked"
    assert result.message is not None and "metadata verification failed" in result.message
