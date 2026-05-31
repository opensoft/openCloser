"""T016 — ``opencloser run3`` CLI contract test.

Implements the 11 assertions enumerated in
``specs/003-real-call-real-crm/contracts/cli-slice3.md`` lines 140-152.

The Typer subcommand surface (``run3_command`` in ``src/opencloser/cli.py``)
exists from the T012 foundational scope. The runner ``run_slice3`` raises
``NotImplementedError`` until T034 + T046 + T047 + T048 + T056 + T057 etc.
land. These tests fail at the runner boundary — each pointing the next
implementation task at the exact behavior to add.

Patterns reused from T013 (see ``t013-clarify-questions.md``): TDD red via
the existing runner stub (Q5 B); fixtures local to this file.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from opencloser.cli import app
from opencloser.slice3.runner import (
    EXIT_CONCURRENT_CLAIM,
    EXIT_LIVE_CALL_ABANDONMENT,
    EXIT_PROVIDER_REJECTED_DIAL,
    EXIT_TELEPHONY_READINESS_FAILURE,
)

_runner = CliRunner()

# Sentinel credential values the test asserts NEVER appear in stdout / run
# report (SC-018). Tests set env vars to these values so any accidental
# logging would surface in the assertion.
SIGNALWIRE_SECRET_SENTINEL = "T016-SIGNALWIRE-CREDENTIAL-must-not-appear"
DATAVERSE_SECRET_SENTINEL = "T016-DATAVERSE-CREDENTIAL-must-not-appear"


@pytest.fixture
def slice3_config(tmp_path: Path) -> Path:
    """A minimal config/slice3.toml in the test's tmp dir."""
    path = tmp_path / "slice3.toml"
    path.write_text(
        '[signalwire]\n'
        'source_caller_id = "+15555550100"\n'
        'status_callback_url_template = "https://test.example.com/sw/status/{session_id}"\n'
        'media_callback_url_template = "https://test.example.com/sw/media/{session_id}"\n\n'
        '[realtime_ai]\n'
        'provider_name = "fake-realtime"\n'
        'model_name = "fake-realtime-1"\n'
        'model_version = "test-0.1"\n\n'
        '[shadow_stt]\n'
        'enabled_default = false\n'
        'discrepancy_policy_path = "config/shadow_stt_discrepancy_policy.json"\n\n'
        '[timeouts]\n'
        'abandonment_sec = 90\n'
        'silence_after_connection_sec = 30\n'
        'grace_window_sec = 3\n\n'
        '[retention]\n'
        'mode = "full_with_redaction"\n\n'
        '[redaction]\n'
        'policy = "default"\n',
        encoding="utf-8",
    )
    return path


@pytest.fixture(autouse=True)
def secret_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set sentinel credentials in the environment so we can scan for leakage."""
    monkeypatch.setenv("SIGNALWIRE_SIGNING_SECRET", SIGNALWIRE_SECRET_SENTINEL)
    monkeypatch.setenv("DATAVERSE_CLIENT_SECRET", DATAVERSE_SECRET_SENTINEL)


def _read_run_report(artifacts_dir: Path) -> dict[str, object] | None:
    """Find the most-recently-written run_report.json under ``artifacts_dir``."""
    candidates = list(artifacts_dir.rglob("run_report.json"))
    if not candidates:
        return None
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return json.loads(latest.read_text(encoding="utf-8"))


# ----------------------------------------------------------------------------
# Assertion 1 — default invocation is rehearsal mode
# ----------------------------------------------------------------------------


def test_default_invocation_is_rehearsal_mode(slice3_config: Path) -> None:
    """``opencloser run3 --campaign-id X --queue-item-id Y`` (no
    ``--real-call``) places 0 SignalWire calls and 0 Dataverse mutations
    (FR-002, SC-011)."""
    result = _runner.invoke(
        app,
        [
            "run3",
            "--campaign-id", "alf-q2",
            "--queue-item-id", "alf-prospect-t016",
            "--config", str(slice3_config),
        ],
    )
    # The runner currently raises NotImplementedError → exit 1. When T034 +
    # T038 land, the rehearsal-mode branch returns 0 (or another expected
    # exit) without dialing or mutating.
    assert result.exit_code == 0, (
        f"rehearsal-mode invocation should exit 0; got {result.exit_code}. "
        f"T034 / T038 must implement rehearsal-mode branch.\n"
        f"stderr/stdout: {result.output!r}"
    )


# ----------------------------------------------------------------------------
# Assertion 2 — real-call flag required for mutation
# ----------------------------------------------------------------------------


def test_real_call_flag_required_for_mutation(slice3_config: Path) -> None:
    """Real-call invocation requires the ``--real-call`` flag; absent →
    rehearsal mode (FR-001, Round 2 Q13)."""
    result_without_flag = _runner.invoke(
        app,
        [
            "run3",
            "--campaign-id", "alf-q2",
            "--queue-item-id", "alf-prospect-t016",
            "--config", str(slice3_config),
        ],
    )
    # Without --real-call, behavior MUST be rehearsal (no mutation).
    # Today the runner raises NotImplementedError → exit 1; T038 must reconcile.
    assert result_without_flag.exit_code == 0, (
        f"rehearsal default must exit 0 without dialing or mutating; "
        f"got {result_without_flag.exit_code}"
    )


# ----------------------------------------------------------------------------
# Assertion 3 — real-call flag required on resume
# ----------------------------------------------------------------------------


def test_real_call_flag_required_on_resume(slice3_config: Path, tmp_path: Path) -> None:
    """Resume invocation without ``--real-call`` runs in rehearsal mode; the
    run report surfaces planned writes; no mutation occurs (Round 2 Q13)."""
    result = _runner.invoke(
        app,
        [
            "run3",
            "--campaign-id", "alf-q2",
            "--queue-item-id", "alf-prospect-t016",
            "--resume", "sess-t016-existing",
            "--operator-id", "operator-b",
            "--config", str(slice3_config),
        ],
    )
    assert result.exit_code == 0, (
        f"resume without --real-call must run in rehearsal mode (exit 0); "
        f"got {result.exit_code}"
    )


# ----------------------------------------------------------------------------
# Assertion 4 — resume preserves the original operator identity
# ----------------------------------------------------------------------------


def test_resume_preserves_original_operator(tmp_path: Path, slice3_config: Path) -> None:
    """Operator A starts a real-call run; operator B re-invokes with
    ``--resume <sid> --real-call --operator-id B`` → the run report contains
    ``operator_identity = {current: B, original: A}`` (Round 2 Q12)."""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    result = _runner.invoke(
        app,
        [
            "run3",
            "--campaign-id", "alf-q2",
            "--queue-item-id", "alf-prospect-t016",
            "--resume", "sess-t016-existing",
            "--real-call",
            "--operator-id", "operator-b",
            "--config", str(slice3_config),
        ],
    )
    # T087 + T088 land the resume coordinator. For TDD red the assertion fails
    # because the runner raises NotImplementedError before producing any artifact.
    report = _read_run_report(artifacts_dir)
    assert report is not None, (
        f"resume invocation must produce a run_report.json under {artifacts_dir}; "
        f"runner exit_code={result.exit_code}, output={result.output!r}"
    )
    identity = report.get("operator_identity")
    assert isinstance(identity, dict)
    assert identity.get("current") == "operator-b", f"current operator must be 'operator-b'; got {identity}"
    assert identity.get("original"), f"original operator must be preserved on resume; got {identity}"


# ----------------------------------------------------------------------------
# Assertion 5 — concurrent claim exits with code 3
# ----------------------------------------------------------------------------


def test_concurrent_claim_exits_with_code_3(slice3_config: Path) -> None:
    """A second invocation on the same already-claimed ``--queue-item-id``
    exits with code 3; no dial, no attempt consumed (Round 1 Q5)."""
    result = _runner.invoke(
        app,
        [
            "run3",
            "--campaign-id", "alf-q2",
            "--queue-item-id", "alf-prospect-t016-already-claimed",
            "--real-call",
            "--config", str(slice3_config),
        ],
    )
    assert result.exit_code == EXIT_CONCURRENT_CLAIM, (
        f"T048 must wire the queue-claim semantics so concurrent invocation exits "
        f"{EXIT_CONCURRENT_CLAIM}; got {result.exit_code}"
    )


# ----------------------------------------------------------------------------
# Assertion 6 — telephony readiness failure exits with code 4
# ----------------------------------------------------------------------------


def test_telephony_readiness_failure_exits_with_code_4(
    tmp_path: Path, slice3_config: Path
) -> None:
    """Any FR-009 readiness check individually failing exits with code 4; the
    readiness report names the failing check (FR-009, FR-011)."""
    result = _runner.invoke(
        app,
        [
            "run3",
            "--campaign-id", "alf-q2",
            "--queue-item-id", "alf-prospect-t016-bad-phone",
            "--real-call",
            "--config", str(slice3_config),
        ],
    )
    assert result.exit_code == EXIT_TELEPHONY_READINESS_FAILURE, (
        f"T046 must wire readiness gating so failures exit "
        f"{EXIT_TELEPHONY_READINESS_FAILURE}; got {result.exit_code}"
    )


# ----------------------------------------------------------------------------
# Assertion 7 — provider-rejected dial exits with code 5
# ----------------------------------------------------------------------------


def test_provider_rejected_dial_exits_with_code_5(slice3_config: Path) -> None:
    """SignalWire 4xx on dial exits with code 5; no attempt consumed; no
    Phone Call activity (FR-012)."""
    result = _runner.invoke(
        app,
        [
            "run3",
            "--campaign-id", "alf-q2",
            "--queue-item-id", "alf-prospect-t016",
            "--real-call",
            "--config", str(slice3_config),
        ],
    )
    # T047 catches ProviderRejectedDialError and maps to EXIT_PROVIDER_REJECTED_DIAL.
    assert result.exit_code == EXIT_PROVIDER_REJECTED_DIAL, (
        f"T047 must map provider 4xx to exit {EXIT_PROVIDER_REJECTED_DIAL}; "
        f"got {result.exit_code}"
    )


# ----------------------------------------------------------------------------
# Assertion 8 — live-call abandonment exits with code 6
# ----------------------------------------------------------------------------


def test_live_call_abandonment_exits_with_code_6(slice3_config: Path) -> None:
    """Configured abandonment timeout elapses → exits with code 6; session
    finalized as ``failed`` / ``live_call_abandonment`` (FR-026 / Round 2 Q6)."""
    result = _runner.invoke(
        app,
        [
            "run3",
            "--campaign-id", "alf-q2",
            "--queue-item-id", "alf-prospect-t016-abandon",
            "--real-call",
            "--config", str(slice3_config),
        ],
    )
    assert result.exit_code == EXIT_LIVE_CALL_ABANDONMENT, (
        f"T056 must map abandonment-timeout outcome to exit "
        f"{EXIT_LIVE_CALL_ABANDONMENT}; got {result.exit_code}"
    )


# ----------------------------------------------------------------------------
# Assertion 9 — run report includes all required FR-036 fields
# ----------------------------------------------------------------------------

# FR-036 (Round 2 amended) required field set — see contracts/cli-slice3.md §"Run report".
_REQUIRED_RUN_REPORT_FIELDS: tuple[str, ...] = (
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


def test_run_report_includes_all_required_fields(
    tmp_path: Path, slice3_config: Path
) -> None:
    """After any invocation, ``run_report.json`` contains all FR-036
    (Round 2-amended) fields."""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    result = _runner.invoke(
        app,
        [
            "run3",
            "--campaign-id", "alf-q2",
            "--queue-item-id", "alf-prospect-t016",
            "--config", str(slice3_config),
        ],
    )
    report = _read_run_report(artifacts_dir)
    assert report is not None, (
        f"every invocation must produce a run_report.json; runner exit_code={result.exit_code}"
    )

    missing = [field for field in _REQUIRED_RUN_REPORT_FIELDS if field not in report]
    assert not missing, (
        f"T033 must populate every FR-036 field; missing: {missing}; "
        f"present: {sorted(report.keys())}"
    )


# ----------------------------------------------------------------------------
# Assertion 10 — DNC-first reflected in per_writeback_operation_status
# ----------------------------------------------------------------------------


def test_dnc_first_reflected_in_per_writeback_operation_status(
    tmp_path: Path, slice3_config: Path
) -> None:
    """On a ``do_not_call`` outcome, ``per_writeback_operation_status[0]
    .operation`` is ``queue_status_update.dnc`` (Round 2 Q14)."""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    result = _runner.invoke(
        app,
        [
            "run3",
            "--campaign-id", "alf-q2",
            "--queue-item-id", "alf-prospect-t016-dnc",
            "--real-call",
            "--config", str(slice3_config),
        ],
    )
    report = _read_run_report(artifacts_dir)
    assert report is not None, (
        f"do_not_call invocation must produce a run_report.json; "
        f"exit_code={result.exit_code}"
    )
    status_list = report.get("per_writeback_operation_status")
    assert isinstance(status_list, list) and status_list, (
        "per_writeback_operation_status must be a non-empty list"
    )
    first = status_list[0]
    assert isinstance(first, dict)
    assert first.get("operation") == "queue_status_update.dnc", (
        f"Round 2 Q14: first per_writeback_operation_status entry on do_not_call "
        f"must be 'queue_status_update.dnc'; got {first}"
    )


# ----------------------------------------------------------------------------
# Assertion 11 — no secrets in stdout or run report (SC-018)
# ----------------------------------------------------------------------------


def test_no_secrets_in_stdout_or_run_report(
    tmp_path: Path, slice3_config: Path
) -> None:
    """grep for any credential env-var value across stdout + run report
    returns 0 matches (SC-018)."""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    result = _runner.invoke(
        app,
        [
            "run3",
            "--campaign-id", "alf-q2",
            "--queue-item-id", "alf-prospect-t016",
            "--config", str(slice3_config),
        ],
    )

    assert SIGNALWIRE_SECRET_SENTINEL not in result.output, (
        f"SC-018: SignalWire signing secret leaked into CLI stdout: {result.output!r}"
    )
    assert DATAVERSE_SECRET_SENTINEL not in result.output, (
        f"SC-018: Dataverse client secret leaked into CLI stdout: {result.output!r}"
    )

    report = _read_run_report(artifacts_dir)
    if report is None:
        # Report not produced (T033 not yet implemented) — the secret-leak
        # assertion can still examine any artifact files that DID land.
        for path in artifacts_dir.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="replace")
                assert SIGNALWIRE_SECRET_SENTINEL not in text, f"secret leaked into {path}"
                assert DATAVERSE_SECRET_SENTINEL not in text, f"secret leaked into {path}"
        pytest.fail(
            "T033 must produce a run_report.json so the SC-018 scan can run on it; "
            "currently no report exists"
        )

    flat = json.dumps(report)
    assert SIGNALWIRE_SECRET_SENTINEL not in flat, "secret leaked into run_report.json"
    assert DATAVERSE_SECRET_SENTINEL not in flat, "secret leaked into run_report.json"
