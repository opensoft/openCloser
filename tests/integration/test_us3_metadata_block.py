"""US3 — Block write-enabled processing when Dataverse metadata cannot be verified.

Covers the FR-002 metadata + operational failure behaviors that MUST block
write-enabled processing (and dry-run for genuine metadata gaps) before any
CRM record is touched. Each test invokes ``run_one_crm_item`` end-to-end and
asserts:

  * ``exit_status == "blocked"`` (the documented FR-002 outcome),
  * an operator-visible message naming the missing/unverifiable item,
  * zero ``fake.created`` / ``fake.patched`` records (SC-007: 0 CRM
    records touched on a metadata block).

Six scenarios per ``tasks.md`` T030:

1. Missing mapped field — the fixture mapping references a field that
   doesn't exist in live Dataverse metadata.
2. Missing option-set value — the mapping declares an integer not present
   in the live picklist.
3. Missing credentials — write-enabled fails hard at the secret-load
   gate (covered in ``tests/integration/test_cli.py``; not re-tested here).
4. Configured-campaign-not-found — currently indistinguishable from
   FR-009 empty-queue no-op (documented gap; the test asserts the
   current behavior so future regressions are caught).
5. Dataverse-unreachable-at-start — live ``verify()`` raises an
   auth/connectivity error; write-enabled blocks, dry-run with
   tolerable status codes proceeds (the latter covered in
   ``test_us2_dry_run.py``).
6. Unverifiable idempotency-key field (SC-015) — the mapping omits
   ``phone_call.idempotency_key`` or ``task.idempotency_key``; readiness
   MUST block 100% of the time.

Plus T028:

7. Malformed redaction policy — an invalid regex pattern in
   ``[redaction]`` fails readiness before any transcript / session write.
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
from opencloser.crm.dataverse.errors import PermanentDataverseError
from opencloser.crm.dataverse.mapping import load_mapping
from opencloser.crm.dataverse.queue_loader import ExplicitId, NextReady
from opencloser.models import RedactionPolicyConfig, RetryConfig, RunMode
from opencloser.slice2.runner import run_one_crm_item
from tests.fixtures.dataverse.helpers import fake_for_mapping
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
_TRANSPORT_FIXTURES = _REPO_ROOT / "tests/fixtures/transport_events"
_CONVERSATIONS = _REPO_ROOT / "tests/fixtures/conversations"

# FrozenClock inside the configured call window for deterministic eligibility.
_CLOCK = FrozenClock(datetime(2026, 5, 22, 19, 0, 0, tzinfo=UTC))


def _write_mapping_variant(
    tmp_path: Path,
    *,
    add_unmapped_option_set: bool = False,
    drop_idempotency_key: str | None = None,
    approved: bool = True,
) -> Path:
    """Copy the fixture mapping with surgical mutations to exercise FR-002 gates.

    - ``add_unmapped_option_set``: append an option-set entry whose integer
      value is not present in the live picklist (exercises
      ``_check_option_set_values``).
    - ``drop_idempotency_key``: ``"phone_call"`` or ``"task"`` — removes the
      corresponding ``*.idempotency_key`` entry to exercise the SC-015
      explicit idempotency-key gate.
    - ``approved``: set ``_meta.approved`` (defaults True so the variant
      reaches gates beyond the approval check; pass False to exercise the
      approval-gate path).

    (Sourcery PR #8 review: dropped the unused ``drop_field`` parameter and
    folded the ``approved`` flag in so tests don't need to mutate the JSON
    twice.)
    """
    raw = json.loads(_MAPPING_FIXTURE.read_text(encoding="utf-8"))
    if drop_idempotency_key is not None:
        key = f"{drop_idempotency_key}.idempotency_key"
        if key in raw["fields"]:
            del raw["fields"][key]
    if add_unmapped_option_set:
        raw["option_sets"]["queue_status.invalid"] = {
            "field": "queue.status",
            "value": 999,  # not in the fixture picklist
        }
    raw["_meta"]["approved"] = approved
    out_path = tmp_path / "mapping-variant.json"
    out_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    return out_path


def _broken_client() -> DataverseClient:
    """A DataverseClient whose token-acquire raises PermanentDataverseError(401)
    — proves the spec §Edge Cases 'Dataverse-unreachable-at-start' path."""

    class _BrokenToken:
        def token(self, *, now: float | None = None) -> str:
            raise PermanentDataverseError(
                "OAuth token acquisition failed (test stub)", status_code=401
            )

    return DataverseClient(
        "https://broken.crm.dynamics.com",
        _BrokenToken(),
        RetryConfig(max_retries=0, backoff_seconds=[1.0], retry_after_cap_seconds=30.0),
        http=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(401))),
        sleep=lambda _seconds: None,
    )


def _run_write_enabled(
    *,
    conn: sqlite3.Connection,
    client,
    artifact_dir: Path,
    slice2_config,
):
    return run_one_crm_item(
        selector=ExplicitId(_QID),
        transport_fixture=_TRANSPORT_FIXTURES / "connected.json",
        conversation_fixture=_CONVERSATIONS / "interested_callback_requested.json",
        slice1_config=_slice1_config(artifact_dir, Path(":memory:")),
        slice2_config=slice2_config,
        client=client,
        conn=conn,
        clock=_CLOCK,
        run_mode=RunMode.WRITE_ENABLED,
    )


# ---------------------------------------------------------------------------
# Scenario 1 — Missing mapped field (FR-002, SC-007)
# ---------------------------------------------------------------------------


def test_us3_blocks_when_mapped_field_missing_in_metadata(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path, tmp_path: Path
) -> None:
    """A field declared in the mapping but not present in live Dataverse
    metadata (via the fake's ``entities`` set) MUST block readiness with an
    operator-visible message naming the unverifiable field."""
    mapping = load_mapping(_MAPPING_FIXTURE)
    # Build a fake whose `medx_callqueueitem` entity is missing one of the
    # mapped attributes (`medx_phonenumber`); `_check_fields` will surface it.
    fake = fake_for_mapping(mapping, _seed())
    fake._entities["medx_callqueueitem"].discard("medx_phonenumber")

    cfg = _slice2_config_shared(mapping_path=_MAPPING_FIXTURE)
    report = _run_write_enabled(
        conn=tmp_state_db,
        client=fake.client(cfg.retry),
        artifact_dir=tmp_artifact_dir,
        slice2_config=cfg,
    )

    assert report.exit_status == "blocked"
    assert report.message is not None
    assert "metadata verification failed" in report.message
    assert "medx_phonenumber" in report.message
    # SC-007 — zero CRM records touched.
    assert fake.created == []
    assert fake.patched == []


# ---------------------------------------------------------------------------
# Scenario 2 — Missing option-set value (FR-002, SC-007)
# ---------------------------------------------------------------------------


def test_us3_blocks_when_option_set_value_missing(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path, tmp_path: Path
) -> None:
    """An option-set value in the mapping that isn't in the live picklist
    MUST block readiness with an operator-visible message naming the value.

    Setup: build the fake from the ORIGINAL mapping (so the live picklist
    only knows the fixture's option-set values), then point Slice2Config
    at a mapping VARIANT that adds an extra `value: 999` for `queue.status`.
    `_check_option_set_values` should flag value 999 as not present in the
    live picklist."""
    original_mapping = load_mapping(_MAPPING_FIXTURE)
    fake = fake_for_mapping(original_mapping, _seed())

    mapping_variant = _write_mapping_variant(tmp_path, add_unmapped_option_set=True)
    cfg = _slice2_config_shared(mapping_path=mapping_variant)
    report = _run_write_enabled(
        conn=tmp_state_db,
        client=fake.client(cfg.retry),
        artifact_dir=tmp_artifact_dir,
        slice2_config=cfg,
    )

    assert report.exit_status == "blocked"
    assert report.message is not None
    assert "queue_status.invalid" in report.message or "999" in report.message
    assert fake.created == []
    assert fake.patched == []


# ---------------------------------------------------------------------------
# Scenario 5 — Dataverse-unreachable-at-start (FR-002, spec §Edge Cases)
# ---------------------------------------------------------------------------


def test_us3_blocks_when_dataverse_unreachable_at_start_in_write_enabled(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """A 401 from `verify()` blocks write-enabled (the dry-run-tolerable
    behavior is exercised in `test_us2_dry_run.py`). Operator sees the
    `metadata verification failed: ...` message; zero CRM records touched."""
    cfg = _slice2_config_shared(mapping_path=_MAPPING_FIXTURE)
    report = _run_write_enabled(
        conn=tmp_state_db,
        client=_broken_client(),
        artifact_dir=tmp_artifact_dir,
        slice2_config=cfg,
    )

    assert report.exit_status == "blocked"
    assert report.message is not None
    assert "metadata verification failed" in report.message
    # _broken_client's fake transport never records creates/patches; assert
    # the run never advanced to a CRM write attempt by checking artifact_dir
    # is None (no session was created).
    assert report.artifact_dir is None


# ---------------------------------------------------------------------------
# Scenario 6 — Unverifiable idempotency-key field (FR-002, FR-024, SC-015)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "drop_kind",
    ["phone_call", "task"],
)
def test_us3_blocks_when_idempotency_key_field_unmapped(
    tmp_state_db: sqlite3.Connection,
    tmp_artifact_dir: Path,
    tmp_path: Path,
    drop_kind: str,
) -> None:
    """SC-015: write-enabled processing MUST be blocked 100% of the time when
    either ``phone_call.idempotency_key`` or ``task.idempotency_key`` is
    unmapped. The explicit T029a check produces a message naming the missing
    key and pointing the operator at ``discover-crm``."""
    mapping_variant = _write_mapping_variant(tmp_path, drop_idempotency_key=drop_kind)
    mapping = load_mapping(mapping_variant)
    fake = fake_for_mapping(mapping, _seed())
    cfg = _slice2_config_shared(mapping_path=mapping_variant)
    report = _run_write_enabled(
        conn=tmp_state_db,
        client=fake.client(cfg.retry),
        artifact_dir=tmp_artifact_dir,
        slice2_config=cfg,
    )

    assert report.exit_status == "blocked"
    assert report.message is not None
    assert f"{drop_kind}.idempotency_key" in report.message
    assert "SC-015" in report.message
    assert fake.created == []
    assert fake.patched == []


# ---------------------------------------------------------------------------
# T028 — Malformed redaction policy (spec §Edge Cases)
# ---------------------------------------------------------------------------


def test_us3_blocks_when_redaction_policy_has_invalid_regex(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """T028 / spec §Edge Cases "Malformed redaction policy": an invalid regex
    pattern in `[redaction]` MUST fail readiness BEFORE any transcript
    write, session creation, queue claim, or CRM write."""
    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = fake_for_mapping(mapping, _seed())

    cfg = _slice2_config_shared(mapping_path=_MAPPING_FIXTURE)
    cfg = cfg.model_copy(
        update={
            "redaction": RedactionPolicyConfig(
                policy="regex",
                retention="full",
                patterns=["[unterminated"],  # invalid regex — unbalanced brackets
            )
        }
    )

    report = _run_write_enabled(
        conn=tmp_state_db,
        client=fake.client(cfg.retry),
        artifact_dir=tmp_artifact_dir,
        slice2_config=cfg,
    )

    assert report.exit_status == "blocked"
    assert report.message is not None
    assert "redaction policy invalid" in report.message
    # Readiness blocked BEFORE any transcript / session / CRM write.
    assert report.artifact_dir is None
    assert fake.created == []
    assert fake.patched == []


# ---------------------------------------------------------------------------
# Scenario 4 — Configured-campaign-not-found (documented gap)
# ---------------------------------------------------------------------------


def test_us3_campaign_not_found_currently_yields_no_callable_item(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """Documented gap: when the configured campaign filter matches zero rows
    (whether because the campaign doesn't exist or because no queue items
    are tagged with it), the queue loader returns ``no-callable-item``.
    Distinguishing the two requires querying the campaign lookup target,
    which depends on the campaign field's mapping type (string vs lookup);
    that distinction is deferred to a follow-up task.

    This test locks in the current behavior so a future regression doesn't
    silently change it: NextReady with a non-existent campaign returns the
    clean no-op, NOT a session creation or attempt increment."""
    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = fake_for_mapping(mapping, _seed())

    cfg = _slice2_config_shared(mapping_path=_MAPPING_FIXTURE)
    report = run_one_crm_item(
        selector=NextReady(campaign="nonexistent-campaign-xyz"),
        transport_fixture=_TRANSPORT_FIXTURES / "connected.json",
        conversation_fixture=_CONVERSATIONS / "interested_callback_requested.json",
        slice1_config=_slice1_config(tmp_artifact_dir, Path(":memory:")),
        slice2_config=cfg,
        client=fake.client(cfg.retry),
        conn=tmp_state_db,
        clock=_CLOCK,
        run_mode=RunMode.WRITE_ENABLED,
    )

    # Documented gap: this is currently `no-callable-item`, not `blocked` per
    # spec §Edge Cases "Configured campaign not found". Tracked as a known
    # limitation; the test asserts the CURRENT behavior so the eventual
    # follow-up can update both this test and the runner together.
    assert report.exit_status == "no-callable-item"
    assert fake.created == []
    assert fake.patched == []
