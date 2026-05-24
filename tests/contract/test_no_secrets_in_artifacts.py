"""T047 — No-secrets-in-artifacts negative-assertion test (FR-005, FR-035).

Runs a write-enabled Slice 2 flow with known-secret env values, then greps
every produced local audit artifact for those exact substrings. Any match
fails the test — even an accidental log capture or a future regression that
serializes the env-var values into a payload would surface here.

Covers spec §FR-005 (secrets MUST NOT be written to logs or exported
artifacts) and §FR-035 (secrets MUST NOT be retained in any local audit
artifact).

Inspection surface, per T047:
  * Run report (currently the CrmRunReport dataclass returned to the CLI —
    serialized here and grepped, since a future `run-report.json` writer
    MUST not leak either).
  * Planned and actual write-back artifacts: writeback.json, task.json.
  * Session-result artifact: session-result.json.
  * Redacted transcript file: transcript.txt (when present).
  * Eligibility-decision artifact: eligibility-decision.json.
  * SQLite rows: every `crm_correlations` and `writeback_progress` row for
    the session — full row serialization, including `last_error`.
  * Run-report message text returned by the runner.
"""

from __future__ import annotations

import dataclasses
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from opencloser.core.clock import FrozenClock
from opencloser.crm.dataverse.mapping import load_mapping
from opencloser.crm.dataverse.queue_loader import ExplicitId
from opencloser.models import RunMode
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

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAPPING_FIXTURE = _REPO_ROOT / "tests/fixtures/dataverse/dataverse_mapping.json"
_TRANSPORT_FIXTURES = _REPO_ROOT / "tests/fixtures/transport_events"
_CONVERSATIONS = _REPO_ROOT / "tests/fixtures/conversations"

_CLOCK = FrozenClock(datetime(2026, 5, 22, 19, 0, 0, tzinfo=UTC))

# Distinctive, low-collision secret values. Each is a contiguous token that
# would never legitimately appear inside an artifact, so any substring match
# is unambiguous evidence of a leak.
_SECRETS: dict[str, str] = {
    "DATAVERSE_TENANT_ID": "SECRET-TENANT-aaaaaaaaaaaaaaaaaaaa",
    "DATAVERSE_CLIENT_ID": "SECRET-CLIENT-bbbbbbbbbbbbbbbbbbbb",
    "DATAVERSE_CLIENT_SECRET": "SECRET-CLIENT-SECRET-cccccccccccccccccccc",
    "DATAVERSE_ENV_URL": "https://SECRET-ENV-dddddddddddddddddddd.crm.dynamics.com",
}


def _walk_artifact_text(session_dir: Path) -> list[tuple[str, str]]:
    """Read every file under ``session_dir`` and return ``(label, content)``
    pairs. Binary files are skipped; everything Slice 2 writes is text/JSON."""
    out: list[tuple[str, str]] = []
    if not session_dir.exists():
        return out
    for path in sorted(session_dir.rglob("*")):
        if path.is_dir():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # An artifact that isn't valid UTF-8 cannot carry the
            # ASCII-printable secrets we set above; safe to skip.
            continue
        out.append((str(path.relative_to(session_dir)), text))
    return out


def _walk_sqlite_rows(conn: sqlite3.Connection, session_id: str) -> list[tuple[str, str]]:
    """Serialize every Slice 2 SQLite row tied to ``session_id`` and return
    ``(label, json)`` pairs ready for substring scanning."""
    out: list[tuple[str, str]] = []
    for table in ("crm_correlations", "writeback_progress", "sessions"):
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE session_id = ?;", (session_id,)
        ).fetchall()
        for i, row in enumerate(rows):
            row_dict = dict(row)
            out.append((f"sqlite:{table}[{i}]", json.dumps(row_dict, sort_keys=True, default=str)))
    return out


def _run_report_text(report) -> str:
    """Serialize the CrmRunReport dataclass for substring scanning. Includes
    every field — even the metadata_report and the message string."""
    as_dict = {f.name: getattr(report, f.name) for f in dataclasses.fields(report)}
    return json.dumps(as_dict, sort_keys=True, default=str)


def test_no_secrets_appear_in_any_audit_artifact(
    tmp_state_db: sqlite3.Connection,
    tmp_artifact_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-005 + FR-035 + T047 — drive a complete write-enabled Slice 2 run
    with known-secret env values, then grep every produced artifact + every
    SQLite row for those exact values. Zero matches must be found."""
    # 1) Plant the secrets in the environment. The runner reads them via
    # `config.py`'s _DATAVERSE_SECRET_ENV map; the auth module passes them to
    # the OAuth token endpoint. The in-process fake's _StubToken ignores
    # these, but the property under test is that they NEVER reach an artifact
    # regardless of what the auth layer does with them.
    for env_name, value in _SECRETS.items():
        monkeypatch.setenv(env_name, value)

    # 2) Drive a normal write-enabled run that produces a full artifact set.
    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = fake_for_mapping(mapping, _seed())
    cfg = _slice2_config_shared(mapping_path=_MAPPING_FIXTURE)
    report = run_one_crm_item(
        selector=ExplicitId(_QID),
        transport_fixture=_TRANSPORT_FIXTURES / "connected.json",
        conversation_fixture=_CONVERSATIONS / "interested_callback_requested.json",
        slice1_config=_slice1_config(tmp_artifact_dir, Path(":memory:")),
        slice2_config=cfg,
        client=fake.client(cfg.retry),
        conn=tmp_state_db,
        clock=_CLOCK,
        run_mode=RunMode.WRITE_ENABLED,
    )
    assert report.exit_status == "completed", (
        f"setup failure: run did not complete; report={report}"
    )
    assert report.session_id is not None
    assert report.artifact_dir is not None

    # 3) Build the full inspection surface.
    leaks: list[tuple[str, str, str]] = []  # (artifact, secret_env, value)
    inspections: list[tuple[str, str]] = []
    inspections.extend(_walk_artifact_text(report.artifact_dir))
    inspections.extend(_walk_sqlite_rows(tmp_state_db, report.session_id))
    inspections.append(("crm_run_report.dataclass", _run_report_text(report)))
    inspections.append(("crm_run_report.message", report.message or ""))

    # Sanity: the inspection surface MUST cover the canonical artifacts; a
    # path silently missing would let a leak through (test of the test).
    artifact_paths = {label for label, _ in inspections}
    for required in ("session-result.json", "writeback.json", "eligibility-decision.json"):
        assert required in artifact_paths, (
            f"inspection surface missing canonical artifact {required!r}; "
            f"covered: {sorted(artifact_paths)}"
        )

    # 4) Literal-substring scan per T047 ("grep for those exact values").
    for label, content in inspections:
        for env_name, secret in _SECRETS.items():
            if secret in content:
                leaks.append((label, env_name, secret))

    assert not leaks, (
        "FR-005/FR-035 violation — secret value(s) leaked into artifact(s):\n  "
        + "\n  ".join(
            f"{label!r} contains {env_name} value {value!r}" for label, env_name, value in leaks
        )
    )
