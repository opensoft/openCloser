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
  `dry_run=True` so zero GET / POST / PATCH operations reach Dataverse
  (FR-031, SC-002, SC-013);
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
from opencloser.models import (
    ArtifactsConfig,
    CallWindowConfig,
    DataverseConfig,
    Disposition,
    EligibilityConfig,
    PersonaConfig,
    RedactionPolicyConfig,
    RetryConfig,
    RunConfig,
    RunMode,
    Slice2Config,
    SliceConfig,
    StateConfig,
    TaskOwnersConfig,
)
from opencloser.slice2.runner import run_one_crm_item
from tests.fixtures.dataverse.helpers import fake_for_mapping

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAPPING_FIXTURE = _REPO_ROOT / "tests/fixtures/dataverse/dataverse_mapping.json"
_CONVERSATIONS = _REPO_ROOT / "tests/fixtures/conversations"
_TRANSPORT_FIXTURES = _REPO_ROOT / "tests/fixtures/transport_events"

_QID = "22222222-2222-2222-2222-222222222222"
_OWNER_CALLBACK = "owner-callback-id"
_OWNER_REVIEW = "owner-review-id"

# FrozenClock inside the configured call window for deterministic eligibility.
_CLOCK = FrozenClock(datetime(2026, 5, 22, 19, 0, 0, tzinfo=UTC))


def _slice1_config(artifact_dir: Path, db_path: Path) -> SliceConfig:
    return SliceConfig(
        call_window=CallWindowConfig(start="09:00", end="20:00"),
        eligibility=EligibilityConfig(max_attempts=5, default_timezone="America/Los_Angeles"),
        artifacts=ArtifactsConfig(dir=str(artifact_dir)),
        persona=PersonaConfig(version="alf-appointment-setter@0.1.0"),
        state=StateConfig(db=str(db_path)),
    )


def _slice2_config(mapping_path: Path = _MAPPING_FIXTURE) -> Slice2Config:
    return Slice2Config(
        # CLI default per FR-031 is dry-run; mirror that here so the config and
        # the explicit run_mode arg below agree.
        run=RunConfig(default_mode=RunMode.DRY_RUN, campaign="alf-q2-davis"),
        dataverse=DataverseConfig(
            mapping_artifact=str(mapping_path),
            callable_status="ready",
        ),
        retry=RetryConfig(max_retries=0, backoff_seconds=[1.0], retry_after_cap_seconds=30.0),
        task_owners=TaskOwnersConfig(callback=_OWNER_CALLBACK, review=_OWNER_REVIEW),
        redaction=RedactionPolicyConfig(policy="regex", retention="full", patterns=[]),
    )


def _seed() -> dict[str, list[dict]]:
    return {
        "account": [{"accountid": "11111111-1111-1111-1111-111111111111", "name": "Sunage ALF"}],
        "medx_callqueueitem": [
            {
                "medx_callqueueitemid": _QID,
                "_medx_accountid_value": "11111111-1111-1111-1111-111111111111",
                "medx_phonenumber": "+15305551234",
                "medx_timezone": "America/Los_Angeles",
                "medx_attemptcount": 0,
                "medx_maxattempts": 5,
                "medx_donotcall": False,
                "medx_callstatus": 0,
                "medx_lastdisposition": None,
                "medx_lastsessionid": None,
                "medx_lasterror": None,
                "medx_nextattemptat": "2026-05-22T16:00:00.000Z",
                "_medx_campaignid_value": "alf-q2-davis",
                "medx_assignedownerid": None,
            }
        ],
        # Dry-run skips owner verification (uses configured default directly),
        # so seeding the owner records is NOT required — but include them so
        # the same seed works if a follow-up test mutates a scenario to
        # write-enabled.
        "systemuser": [
            {"systemuserid": _OWNER_CALLBACK, "isdisabled": False},
            {"systemuserid": _OWNER_REVIEW, "isdisabled": False},
        ],
    }


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


# ---------------------------------------------------------------------------
# Spec §Edge Cases "Dry-run requested but write credentials are absent" —
# dry-run readiness skips live `verify()` even when it would fail in write-enabled.
# ---------------------------------------------------------------------------


def _stub_no_dataverse_client() -> DataverseClient:
    """Build a DataverseClient whose underlying httpx transport hard-fails on any
    request. Proves that dry-run readiness completes WITHOUT touching Dataverse
    (it never reaches `verify()`). The downstream queue load DOES use the
    client; this stub is only consumed for the readiness-path assertion, so the
    test uses a real fake client for the queue load."""

    def _refuse(_request: httpx.Request) -> httpx.Response:
        raise AssertionError(
            "dry-run readiness MUST NOT issue any HTTP request to Dataverse — "
            "spec §Edge Cases 'Dry-run requested but write credentials are absent'"
        )

    transport = httpx.MockTransport(_refuse)

    class _StubToken:
        def acquire(self) -> str:
            raise AssertionError(
                "dry-run readiness MUST NOT acquire an OAuth token when write "
                "credentials are absent"
            )

    return DataverseClient(
        "https://stub.crm.dynamics.com",
        _StubToken(),
        RetryConfig(max_retries=0, backoff_seconds=[1.0], retry_after_cap_seconds=30.0),
        http=httpx.Client(transport=transport),
        sleep=lambda _seconds: None,
    )


def test_us2_dry_run_readiness_skips_live_verify(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """Confirms that dry-run readiness validates only the local mapping artifact
    and DOES NOT call live `verify()` — so a missing-credentials environment that
    would block a write-enabled run still produces a successful dry-run readiness
    (the queue load is a separate concern, exercised against a working fake)."""
    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = fake_for_mapping(mapping, _seed())

    # Use the real fake for the queue load. The proof here is the absence of any
    # `verify()` call: the metadata-verification report on the returned
    # CrmRunReport is the synthetic placeholder, NOT a live report. (`verify()`
    # populates `drift` from the live discover; the dry-run placeholder leaves
    # `drift` empty by construction.)
    report = _run_dry(
        conn=tmp_state_db,
        client=fake.client(_slice2_config().retry),
        transport_fixture="connected",
        conversation_fixture="interested_callback_requested",
        artifact_dir=tmp_artifact_dir,
    )

    assert report.exit_status == "completed"
    assert report.metadata_report is not None
    # Synthetic dry-run placeholder: ok=True, no missing, no drift.
    assert report.metadata_report.ok is True
    assert report.metadata_report.missing == []
    assert report.metadata_report.drift == []


def test_us2_dry_run_readiness_stub_client_proves_no_oauth(
    tmp_path: Path,
) -> None:
    """Lower-level proof: invoke `_verify_readiness` directly with a stub client
    whose token-acquire AND HTTP transport both `AssertionError` on any call.
    Dry-run readiness must complete without raising — this proves it never
    touches the client (and so does not need write credentials)."""
    from opencloser.slice2.runner import _verify_readiness

    cfg = _slice2_config()
    stub_client = _stub_no_dataverse_client()

    result = _verify_readiness(cfg, stub_client, _CLOCK, dry_run=True)

    # The synthetic placeholder return path — readiness succeeded without HTTP.
    from opencloser.slice2.runner import _ReadinessResult

    assert isinstance(result, _ReadinessResult)
    assert result.metadata_report.ok is True
    assert result.metadata_report.checked_at == _CLOCK.now_utc_ms()
