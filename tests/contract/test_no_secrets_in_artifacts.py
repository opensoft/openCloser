"""T047 — No-secrets-in-artifacts negative-assertion test (FR-005, FR-035).

Runs Slice 2 flows (success + failure paths) with known-secret env values,
then greps every produced local audit artifact for those exact substrings.
Any match fails the test — even an accidental log capture or a future
regression that serializes env-var values into a payload would surface here.

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
  * SQLite rows: every `crm_correlations`, `writeback_progress`, and
    `sessions` row for the session — full row serialization, including
    `last_error`.
  * Run-report message text returned by the runner.

Failure-path coverage (post-2026-05-24 audit / Pass 1A): the success-only
variant of this test silently bypassed the actual leak surface
(`writeback_progress.last_error`, `CrmRunReport.message` populated by
Permanent/TransientDataverseError formatters). The Dataverse-failure
variant below drives a 401 against the fake to exercise those formatters,
and the unit-level tests at the bottom of this file pin the redaction
contracts on the error wrappers directly so a regression in `auth.py` /
`errors.py` formatter strings surfaces here even when the e2e fake can't
reproduce a real OAuth failure.
"""

from __future__ import annotations

import dataclasses
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from opencloser.core.clock import FrozenClock
from opencloser.crm.dataverse.auth import _auth_status_error, _wrap_auth_transport_error
from opencloser.crm.dataverse.errors import (
    PermanentDataverseError,
    TransientDataverseError,
    raise_for_dataverse_response,
)
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


# ---------------------------------------------------------------------------
# Inspection helpers
# ---------------------------------------------------------------------------


def _walk_artifact_text(session_dir: Path | None) -> list[tuple[str, str]]:
    """Read every file under ``session_dir`` and return ``(label, content)``
    pairs. Binary files are skipped; everything Slice 2 writes is text/JSON."""
    out: list[tuple[str, str]] = []
    if session_dir is None or not session_dir.exists():
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


def _walk_sqlite_rows(
    conn: sqlite3.Connection, session_id: str | None
) -> list[tuple[str, str, int]]:
    """Serialize every Slice 2 SQLite row tied to ``session_id`` and return
    ``(label, json, row_count_for_table)`` tuples ready for substring scanning
    plus row-count assertions."""
    out: list[tuple[str, str, int]] = []
    if session_id is None:
        return out
    for table in ("crm_correlations", "writeback_progress", "sessions"):
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE session_id = ?;", (session_id,)
        ).fetchall()
        for i, row in enumerate(rows):
            row_dict = dict(row)
            out.append(
                (
                    f"sqlite:{table}[{i}]",
                    json.dumps(row_dict, sort_keys=True, default=str),
                    len(rows),
                )
            )
    return out


def _run_report_text(report: Any) -> str:
    """Serialize the CrmRunReport dataclass for substring scanning. Includes
    every field — even the metadata_report and the message string."""
    as_dict = {f.name: getattr(report, f.name) for f in dataclasses.fields(report)}
    return json.dumps(as_dict, sort_keys=True, default=str)


def _scan_for_leaks(inspections: list[tuple[str, str]]) -> list[tuple[str, str, str]]:
    """Literal-substring scan per T047 ('grep for those exact values').
    Returns a list of ``(artifact_label, env_var_name, leaked_value)`` tuples."""
    leaks: list[tuple[str, str, str]] = []
    for label, content in inspections:
        for env_name, secret in _SECRETS.items():
            if secret in content:
                leaks.append((label, env_name, secret))
    return leaks


def _build_inspection_surface(
    conn: sqlite3.Connection,
    session_dir: Path | None,
    session_id: str | None,
    report: Any,
) -> tuple[list[tuple[str, str]], dict[str, int]]:
    """Build the full inspection surface for a session run. Returns:
      * inspections list of ``(label, content)`` pairs for grepping
      * per-table row counts for assertion
    """
    inspections: list[tuple[str, str]] = []
    inspections.extend(_walk_artifact_text(session_dir))
    row_counts: dict[str, int] = {
        "crm_correlations": 0,
        "writeback_progress": 0,
        "sessions": 0,
    }
    for label, content, count in _walk_sqlite_rows(conn, session_id):
        inspections.append((label, content))
        table = label.split(":", 1)[1].split("[", 1)[0]
        row_counts[table] = count
    inspections.append(("crm_run_report.dataclass", _run_report_text(report)))
    inspections.append(("crm_run_report.message", report.message or ""))
    return inspections, row_counts


def _plant_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set every T047 secret env value to a distinctive recognisable token."""
    for env_name, value in _SECRETS.items():
        monkeypatch.setenv(env_name, value)


# ---------------------------------------------------------------------------
# End-to-end leak scans — success path + Dataverse-failure path
# ---------------------------------------------------------------------------


def test_no_secrets_in_artifacts_success_path(
    tmp_state_db: sqlite3.Connection,
    tmp_artifact_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-005 + FR-035 — successful write-enabled run with secret env values
    plants no secret strings in any produced artifact or SQLite row. Locks
    in the happy-path inspection surface; failure-path leakage is covered by
    ``test_no_secrets_in_artifacts_dataverse_failure_path`` below."""
    _plant_secrets(monkeypatch)

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

    inspections, row_counts = _build_inspection_surface(
        tmp_state_db, report.artifact_dir, report.session_id, report
    )

    # Sanity: tighter required-artifact list — every canonical artifact a
    # write-enabled interested_callback_requested run produces MUST be in the
    # inspection surface. A path silently missing would let a leak through.
    artifact_paths = {label for label, _ in inspections}
    for required in (
        "session-result.json",
        "writeback.json",
        "task.json",
        "eligibility-decision.json",
        "transcript.txt",
    ):
        assert required in artifact_paths, (
            f"inspection surface missing canonical artifact {required!r}; "
            f"covered: {sorted(artifact_paths)}"
        )
    # Sanity: SQLite row counts must be nonzero — a vacuous "0 rows scanned"
    # passes any substring test trivially. Write-enabled flow MUST produce at
    # least 1 row per Slice 2 table for the session.
    for table, n in row_counts.items():
        assert n > 0, (
            f"sanity failure: {table!r} contains 0 rows for session "
            f"{report.session_id!r} — the inspection surface scanned nothing "
            f"for this table and would silently pass a leak. row_counts={row_counts}"
        )

    leaks = _scan_for_leaks(inspections)
    assert not leaks, (
        "FR-005/FR-035 violation — secret value(s) leaked into artifact(s):\n  "
        + "\n  ".join(
            f"{label!r} contains {env_name} value {value!r}" for label, env_name, value in leaks
        )
    )


def test_no_secrets_in_artifacts_dataverse_failure_path(
    tmp_state_db: sqlite3.Connection,
    tmp_artifact_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-005 + FR-035 (Pass 1A — post-audit hardening) — the *failure* path
    is where pre-redaction error formatters previously leaked tenant_id and
    env_url host into ``CrmRunReport.message`` + ``writeback_progress.last_error``
    + stdout. This test forces the fake to return HTTP 401 on the first
    metadata-verify request, drives the runner through its error-formatting
    code path, then greps the result for any of the 4 known-secret env
    values. Zero matches must be found."""
    _plant_secrets(monkeypatch)

    mapping = load_mapping(_MAPPING_FIXTURE)
    fake = fake_for_mapping(mapping, _seed())
    # 401 on the very first Dataverse request (the verify() entity-def GET).
    # The runner converts the resulting PermanentDataverseError into a
    # CrmRunReport(exit_status="blocked", message="metadata verification failed: ...").
    fake.fail_next(1, status=401)

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
    # 401 at readiness → blocked exit (per runner's _verify_readiness handler).
    assert report.exit_status == "blocked", (
        f"setup failure: forced 401 didn't produce a blocked exit; report={report}"
    )

    inspections, _ = _build_inspection_surface(
        tmp_state_db, report.artifact_dir, report.session_id, report
    )

    # The message MUST exist (the runner populates it on every blocked exit).
    assert report.message is not None and len(report.message) > 0, (
        "blocked exit must carry a non-empty operator-visible message"
    )
    # And the formatted URL portion MUST be present in the message (proving
    # the test actually exercises the formatter, not a different code path).
    assert "<env>" in report.message, (
        "expected the redacted '<env>' marker in the failure message; "
        f"got: {report.message!r}"
    )

    leaks = _scan_for_leaks(inspections)
    assert not leaks, (
        "FR-005/FR-035 violation — secret value(s) leaked into FAILURE-path "
        "artifact(s) (this is the surface the success-only T047 missed):\n  "
        + "\n  ".join(
            f"{label!r} contains {env_name} value {value!r}" for label, env_name, value in leaks
        )
    )


# ---------------------------------------------------------------------------
# Unit-level redaction-contract tests on the error formatters themselves.
# These pin the redaction property to the formatter functions so a regression
# would surface even without a working e2e auth-failure fake.
# ---------------------------------------------------------------------------


def test_auth_transport_error_formatter_redacts_tenant_id() -> None:
    """``_wrap_auth_transport_error`` MUST NOT include the real tenant id in
    its exception message. The redacted constant
    ``<redacted-tenant>`` must appear instead."""
    tenant_id = "SECRET-TENANT-zzzzzzzzzzzzzzzzzzzz"
    # Build a httpx.TimeoutException whose request URL embeds the tenant id;
    # this mimics what real `httpx.post(<token-endpoint>)` would raise when
    # the endpoint is unreachable.
    req = httpx.Request(
        "POST", f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    )
    exc = httpx.ConnectTimeout("simulated timeout", request=req)

    result = _wrap_auth_transport_error(exc)

    rendered = f"{type(result).__name__}: {result}"
    assert tenant_id not in rendered, (
        f"FR-005 violation: tenant id leaked into "
        f"_wrap_auth_transport_error result: {rendered!r}"
    )
    assert "<redacted-tenant>" in rendered, (
        f"expected redaction marker in formatter output; got: {rendered!r}"
    )
    # The redaction must work for both transient (timeout/network) and
    # permanent (other HTTPError subtypes) wrappers.
    perm_exc = httpx.UnsupportedProtocol("simulated protocol error", request=req)
    perm_result = _wrap_auth_transport_error(perm_exc)
    perm_rendered = f"{type(perm_result).__name__}: {perm_result}"
    assert tenant_id not in perm_rendered
    assert "<redacted-tenant>" in perm_rendered


def test_auth_status_error_formatter_redacts_tenant_id() -> None:
    """``_auth_status_error`` MUST NOT include the real tenant id in its
    exception message for any HTTP status."""
    tenant_id = "SECRET-TENANT-yyyyyyyyyyyyyyyyyyyy"
    req = httpx.Request(
        "POST", f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    )

    # Permanent: HTTP 401 (invalid_client)
    resp_401 = httpx.Response(401, request=req, json={"error": "invalid_client"})
    perm = _auth_status_error(resp_401)
    perm_rendered = f"{type(perm).__name__}: {perm}"
    assert tenant_id not in perm_rendered
    assert "<redacted-tenant>" in perm_rendered

    # Transient: HTTP 429 (throttled)
    resp_429 = httpx.Response(429, request=req, headers={"Retry-After": "5"})
    transient = _auth_status_error(resp_429)
    transient_rendered = f"{type(transient).__name__}: {transient}"
    assert tenant_id not in transient_rendered
    assert "<redacted-tenant>" in transient_rendered


def test_dataverse_response_error_formatter_redacts_env_url_host() -> None:
    """``raise_for_dataverse_response`` MUST NOT include the env_url host or
    the query string in the exception message. Only the URL PATH survives."""
    env_url = "https://SECRET-ENV-zzzzzzzzzzzzzzzzzzzz.crm.dynamics.com"
    req = httpx.Request(
        "GET",
        f"{env_url}/api/data/v9.2/medx_callqueueitems?$filter=medx_callqueueitemid eq 'q-1'",
    )

    # Permanent path (401)
    resp_401 = httpx.Response(401, request=req)
    with pytest.raises(PermanentDataverseError) as exc_info_p:
        raise_for_dataverse_response(resp_401)
    perm_rendered = str(exc_info_p.value)
    assert env_url not in perm_rendered, (
        f"FR-005 violation: env_url leaked into raise_for_dataverse_response "
        f"output: {perm_rendered!r}"
    )
    # Host stripped, but path preserved + `<env>` marker visible.
    assert "<env>" in perm_rendered
    assert "/api/data/v9.2/medx_callqueueitems" in perm_rendered
    # Query string also stripped (the GUID in $filter would be sensitive too).
    assert "q-1" not in perm_rendered

    # Transient path (503)
    resp_503 = httpx.Response(503, request=req)
    with pytest.raises(TransientDataverseError) as exc_info_t:
        raise_for_dataverse_response(resp_503)
    transient_rendered = str(exc_info_t.value)
    assert env_url not in transient_rendered
    assert "<env>" in transient_rendered
