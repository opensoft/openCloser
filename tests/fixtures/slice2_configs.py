"""Shared Slice 2 test-config + seed builders (US1, US2, future US3/US4 share these).

Extracted from ``tests/integration/test_us1_write_enabled.py`` and
``tests/integration/test_us2_dry_run.py`` so adding a new user-story test file
does not re-duplicate the ~50 LoC of fixture wiring (per SonarCloud's
new-code duplication threshold).
"""

from __future__ import annotations

from pathlib import Path

from opencloser.models import (
    ArtifactsConfig,
    CallWindowConfig,
    DataverseConfig,
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

# Stable IDs used by every Slice 2 integration test seed.
QID = "22222222-2222-2222-2222-222222222222"
ACCOUNT_ID = "11111111-1111-1111-1111-111111111111"
OWNER_CALLBACK = "owner-callback-id"
OWNER_REVIEW = "owner-review-id"


def slice1_config(artifact_dir: Path, db_path: Path) -> SliceConfig:
    """Slice 1 config the integration tests use (within-call-window, max 5 attempts)."""
    return SliceConfig(
        call_window=CallWindowConfig(start="09:00", end="20:00"),
        eligibility=EligibilityConfig(max_attempts=5, default_timezone="America/Los_Angeles"),
        artifacts=ArtifactsConfig(dir=str(artifact_dir)),
        persona=PersonaConfig(version="alf-appointment-setter@0.1.0"),
        state=StateConfig(db=str(db_path)),
    )


def slice2_config(
    *,
    mapping_path: Path,
    default_mode: RunMode = RunMode.WRITE_ENABLED,
    campaign: str = "alf-q2-davis",
) -> Slice2Config:
    """Slice 2 config the integration tests use. ``mapping_path`` is the path to
    a verified mapping artifact; ``default_mode`` sets ``[run].default_mode``."""
    return Slice2Config(
        run=RunConfig(default_mode=default_mode, campaign=campaign),
        dataverse=DataverseConfig(
            mapping_artifact=str(mapping_path),
            callable_status="ready",
        ),
        retry=RetryConfig(max_retries=0, backoff_seconds=[1.0], retry_after_cap_seconds=30.0),
        task_owners=TaskOwnersConfig(callback=OWNER_CALLBACK, review=OWNER_REVIEW),
        redaction=RedactionPolicyConfig(policy="regex", retention="full", patterns=[]),
    )


def seed(
    *,
    phone: str = "+15305551234",
    status: int = 0,
    dnc: bool = False,
    override_owner: str | None = None,
) -> dict[str, list[dict]]:
    """Seed rows for the in-process Dataverse fake — one `ready` queue item +
    its Account + the default callback/review owners.

    The owner records are needed by the FR-025 verification path in
    write-enabled mode; dry-run tests don't strictly need them but inherit them
    so the same seed works across modes.
    """
    return {
        "account": [{"accountid": ACCOUNT_ID, "name": "Sunage ALF"}],
        "medx_callqueueitem": [
            {
                "medx_callqueueitemid": QID,
                "_medx_accountid_value": ACCOUNT_ID,
                "medx_phonenumber": phone,
                "medx_timezone": "America/Los_Angeles",
                "medx_attemptcount": 0,
                "medx_maxattempts": 5,
                "medx_donotcall": dnc,
                "medx_callstatus": status,
                "medx_lastdisposition": None,
                "medx_lastsessionid": None,
                "medx_lasterror": None,
                "medx_nextattemptat": "2026-05-22T16:00:00.000Z",
                "_medx_campaignid_value": "alf-q2-davis",
                "medx_assignedownerid": override_owner,
            }
        ],
        "systemuser": [
            {"systemuserid": OWNER_CALLBACK, "isdisabled": False},
            {"systemuserid": OWNER_REVIEW, "isdisabled": False},
        ],
    }
