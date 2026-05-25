"""N7 — CLI integration tests for the three Typer subcommands (FR-025 / FR-026 / FR-027).

Exercises `init-state`, `load-queue-item`, and `run-one` through Typer's `CliRunner`:
the happy path (eligible → connected → finalized), the blocked-by-eligibility path,
and the unknown-queue-item-id error path. `cli.py` is otherwise untested, so this
file closes the coverage gap that drags the suite below the 90% gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from opencloser.cli import app

pytestmark = pytest.mark.integration

_REPO = Path(__file__).resolve().parents[2]
_QUEUE_FIXTURES = _REPO / "tests/fixtures/queue_items"
_CONV_FIXTURE = _REPO / "tests/fixtures/conversations/interested_callback_requested.json"
_TRANSPORT_FIXTURE = _REPO / "tests/fixtures/transport_events/connected.json"

_runner = CliRunner()


def _write_config(tmp_path: Path, persona_version: str = "alf-appointment-setter@0.1.0") -> Path:
    """Write a slice1.toml pointing state + artifacts at the test's temp dir.

    The call window is widened to the full day so the eligibility rule (c) outcome is
    deterministic regardless of the wall-clock time the test happens to run at — the
    CLI uses a real `SystemClock` (no clock-injection seam on the operator surface).
    """
    state_db = (tmp_path / "state" / "slice1.db").as_posix()
    artifacts_dir = (tmp_path / "artifacts").as_posix()
    config_path = tmp_path / "slice1.toml"
    config_path.write_text(
        "[call_window]\n"
        'start = "00:00"\n'
        'end = "23:59"\n\n'
        "[eligibility]\n"
        "max_attempts = 5\n"
        'default_timezone = "America/Los_Angeles"\n\n'
        "[artifacts]\n"
        f'dir = "{artifacts_dir}"\n'
        'schema_version = "slice1-v1"\n\n'
        "[persona]\n"
        f'version = "{persona_version}"\n\n'
        "[state]\n"
        f'db = "{state_db}"\n',
        encoding="utf-8",
    )
    return config_path


def _combined_output(result) -> str:
    """Return stdout + stderr regardless of how the runner separated the streams."""
    text = result.output or ""
    try:
        if result.stderr:
            text += result.stderr
    except (ValueError, AttributeError):
        # Older/newer runners may mix the streams or not expose `.stderr` standalone.
        pass
    return text


def test_cli_run_one_happy_path(tmp_path: Path) -> None:
    """init-state → load-queue-item → run-one for an eligible record reaches a
    finalized `interested_callback_requested` disposition and prints the FR-027 surface."""
    config_path = _write_config(tmp_path)

    init = _runner.invoke(app, ["init-state", "--config", str(config_path)])
    assert init.exit_code == 0, _combined_output(init)
    assert "slice1-v1 applied" in init.output

    load = _runner.invoke(
        app,
        [
            "load-queue-item",
            "--file",
            str(_QUEUE_FIXTURES / "alf-prospect-001.json"),
            "--config",
            str(config_path),
        ],
    )
    assert load.exit_code == 0, _combined_output(load)
    assert "alf-prospect-001" in load.output

    run = _runner.invoke(
        app,
        [
            "run-one",
            "--queue-item-id",
            "alf-prospect-001",
            "--conversation-fixture",
            str(_CONV_FIXTURE),
            "--transport-fixture",
            str(_TRANSPORT_FIXTURE),
            "--config",
            str(config_path),
        ],
    )
    assert run.exit_code == 0, _combined_output(run)
    # FR-027 operator output surface.
    assert "eligibility:             allow" in run.output
    assert "final_disposition:       interested_callback_requested" in run.output
    assert "wall_time_ms:" in run.output
    assert "session-result.json" in run.output


def test_cli_run_one_blocked_path(tmp_path: Path) -> None:
    """A DNC-flagged record is blocked by eligibility — no transport/conversation
    fixtures needed, `mock_provider_call_id` is absent, disposition is `blocked`."""
    config_path = _write_config(tmp_path)

    assert _runner.invoke(app, ["init-state", "--config", str(config_path)]).exit_code == 0
    load = _runner.invoke(
        app,
        [
            "load-queue-item",
            "--file",
            str(_QUEUE_FIXTURES / "alf-prospect-dnc.json"),
            "--config",
            str(config_path),
        ],
    )
    assert load.exit_code == 0, _combined_output(load)

    run = _runner.invoke(
        app,
        [
            "run-one",
            "--queue-item-id",
            "alf-prospect-dnc",
            "--config",
            str(config_path),
        ],
    )
    assert run.exit_code == 0, _combined_output(run)
    assert "eligibility:             block" in run.output
    assert "final_disposition:       blocked" in run.output
    assert "mock_provider_call_id:   <none>" in run.output


def test_cli_run_one_unknown_queue_item_id_exits_2(tmp_path: Path) -> None:
    """An unknown queue-item ID surfaces a clear error and exits with code 2."""
    config_path = _write_config(tmp_path)
    assert _runner.invoke(app, ["init-state", "--config", str(config_path)]).exit_code == 0

    run = _runner.invoke(
        app,
        [
            "run-one",
            "--queue-item-id",
            "does-not-exist-xyz",
            "--config",
            str(config_path),
        ],
    )
    assert run.exit_code == 2
    assert "queue_item_id not found" in _combined_output(run)


def test_cli_run_one_missing_transport_fixture_exits_2(tmp_path: Path) -> None:
    """An eligible record run without --transport-fixture surfaces the orchestrator's
    ValueError as a clean `error:` line + exit code 2 — not an uncaught traceback."""
    config_path = _write_config(tmp_path)
    assert _runner.invoke(app, ["init-state", "--config", str(config_path)]).exit_code == 0
    load = _runner.invoke(
        app,
        [
            "load-queue-item",
            "--file",
            str(_QUEUE_FIXTURES / "alf-prospect-001.json"),
            "--config",
            str(config_path),
        ],
    )
    assert load.exit_code == 0, _combined_output(load)

    run = _runner.invoke(
        app,
        ["run-one", "--queue-item-id", "alf-prospect-001", "--config", str(config_path)],
    )
    assert run.exit_code == 2
    out = _combined_output(run)
    assert "error:" in out
    assert "transport_fixture_id is required" in out


def test_cli_run_one_persona_version_mismatch_exits_2(tmp_path: Path) -> None:
    """A config persona.version that doesn't match the available persona fails fast
    with a clear error + exit code 2, before any state work."""
    config_path = _write_config(tmp_path, persona_version="alf-appointment-setter@9.9.9")

    run = _runner.invoke(
        app,
        ["run-one", "--queue-item-id", "alf-prospect-001", "--config", str(config_path)],
    )
    assert run.exit_code == 2
    out = _combined_output(run)
    assert "error:" in out
    assert "persona.version" in out


def test_cli_run_one_missing_transport_fixture_path_exits_2(tmp_path: Path) -> None:
    """A --transport-fixture pointing at a nonexistent file surfaces a clean
    `error:` line + exit code 2, not an uncaught FileNotFoundError traceback."""
    config_path = _write_config(tmp_path)
    assert _runner.invoke(app, ["init-state", "--config", str(config_path)]).exit_code == 0
    load = _runner.invoke(
        app,
        [
            "load-queue-item",
            "--file",
            str(_QUEUE_FIXTURES / "alf-prospect-001.json"),
            "--config",
            str(config_path),
        ],
    )
    assert load.exit_code == 0, _combined_output(load)

    run = _runner.invoke(
        app,
        [
            "run-one",
            "--queue-item-id",
            "alf-prospect-001",
            "--transport-fixture",
            str(tmp_path / "nope.json"),
            "--config",
            str(config_path),
        ],
    )
    assert run.exit_code == 2
    out = _combined_output(run)
    assert "error:" in out
    assert "not found" in out.lower()


def test_cli_run_one_malformed_conversation_fixture_exits_2(tmp_path: Path) -> None:
    """A conversation fixture whose turn is missing 'role'/'text' surfaces a clean
    error + exit code 2, not an uncaught KeyError traceback."""
    config_path = _write_config(tmp_path)
    bad = tmp_path / "bad_conv.json"
    bad.write_text('{"turns": [{"role": "contact"}]}', encoding="utf-8")
    run = _runner.invoke(
        app,
        [
            "run-one",
            "--queue-item-id",
            "alf-prospect-001",
            "--conversation-fixture",
            str(bad),
            "--config",
            str(config_path),
        ],
    )
    assert run.exit_code == 2
    out = _combined_output(run)
    assert "error:" in out
    assert "turn" in out.lower()


def test_cli_no_args_shows_help() -> None:
    """`no_args_is_help=True`: invoking the app with no subcommand prints help."""
    result = _runner.invoke(app, [])
    # Typer exits 0 (or 2 on some versions) for the no-args help screen; the help text
    # is what matters for the operator.
    assert "init-state" in result.output
    assert "load-queue-item" in result.output
    assert "run-one" in result.output


# ---------------------------------------------------------------------------
# Slice 2 — run-crm input validation (GUID shape, dry-run gate)
# ---------------------------------------------------------------------------


def test_cli_run_crm_rejects_non_guid_queue_item_id(tmp_path: Path) -> None:
    """`--queue-item-id` MUST be a Dataverse GUID — arbitrary strings interpolated
    into the OData $filter / record URL are a filter-injection vector."""
    config_path = _write_config(tmp_path)
    run = _runner.invoke(
        app,
        [
            "run-crm",
            "--write",
            "--queue-item-id",
            "not-a-guid",
            "--transport-fixture",
            str(_TRANSPORT_FIXTURE),
            "--config",
            str(config_path),
        ],
    )
    assert run.exit_code == 2
    out = _combined_output(run)
    assert "error:" in out
    assert "not a valid Dataverse GUID" in out


@pytest.mark.parametrize(
    "bad_guid",
    [
        "22222222-2222-2222-2222-222222222222\n",  # trailing newline (Python `$` matches before \n)
        "22222222-2222-2222-2222-222222222222 ",  # trailing space
        "22222222-2222-2222-2222-222222222222extra",  # extra characters
        "\n22222222-2222-2222-2222-222222222222",  # leading newline
        "22222222-2222-2222-2222-222222222222\n22222222-2222-2222-2222-222222222222",  # second GUID after newline
    ],
)
def test_cli_run_crm_rejects_guid_with_trailing_or_extra_chars(
    tmp_path: Path, bad_guid: str
) -> None:
    """Copilot PR #3 LOW (security): `_GUID_RE` uses `.fullmatch` (not `.match`)
    so a trailing newline / whitespace / extra characters cannot slip past the
    `^…$` anchor. Python's `$` matches before a final `\\n` by default, so
    `.match()` against an `^…$` pattern would accept `<valid-guid>\\n` and
    interpolate it into OData URLs/filters."""
    config_path = _write_config(tmp_path)
    run = _runner.invoke(
        app,
        [
            "run-crm",
            "--write",
            "--queue-item-id",
            bad_guid,
            "--transport-fixture",
            str(_TRANSPORT_FIXTURE),
            "--config",
            str(config_path),
        ],
    )
    assert run.exit_code == 2
    out = _combined_output(run)
    assert "not a valid Dataverse GUID" in out


def test_cli_run_crm_without_write_defaults_to_dry_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`run-crm` without `--write` enters the FR-031 dry-run path (the previous
    "dry-run not implemented" placeholder was removed in US2; the
    missing-credentials gate was softened in round-2 review per Codex feedback).

    With the Dataverse secret env vars absent in the test environment, the CLI
    now:
      1. Emits a `warning:` instead of `error:` for the missing secrets,
      2. Proceeds into the dry-run path with placeholder credentials,
      3. Fails AT the first network step (the placeholder creds can't
         authenticate against the placeholder env_url) — exit_status="failed",
         which the `_EXIT_CODE` table maps to CLI exit code 2.

    Codex PR #3 follow-up (post-swarm): the previous version of this test
    relied on the placeholder credentials failing at REAL outbound Entra +
    Dataverse calls, which made the suite non-hermetic — flaky in CI without
    DNS/egress and a slow no-network failure. We now monkeypatch
    `DataverseTokenProvider.token` to raise immediately, so the same observable
    behavior (warning + non-zero exit) is asserted with zero network I/O."""
    from opencloser.crm.dataverse.auth import DataverseTokenProvider
    from opencloser.crm.dataverse.errors import PermanentDataverseError

    def _fail_token(self, *, now: float | None = None) -> str:
        # 401 from Entra is the natural failure shape for placeholder creds.
        # Wrapped redacted to mirror the production error formatter (FR-005).
        raise PermanentDataverseError(
            "OAuth token acquisition failed (placeholder credentials)",
            status_code=401,
        )

    monkeypatch.setattr(DataverseTokenProvider, "token", _fail_token)

    config_path = _write_config(tmp_path)
    run = _runner.invoke(
        app,
        [
            "run-crm",
            "--queue-item-id",
            "22222222-2222-2222-2222-222222222222",
            "--transport-fixture",
            str(_TRANSPORT_FIXTURE),
            "--config",
            str(config_path),
        ],
    )
    out = _combined_output(run)
    # The removed "dry-run not yet implemented" placeholder is gone.
    assert "dry-run is not yet implemented" not in out.lower()
    # The missing-secrets gate is now a WARNING (not a fatal error) in dry-run,
    # per Codex PR #7 review + spec §Edge Cases.
    assert "warning" in out.lower() and "missing required dataverse secret" in out.lower()
    # Run reaches the dry-run path; the placeholder credentials fail at the
    # first network step (now stubbed), producing exit_status="failed" (CLI
    # exit code 2 per `_EXIT_CODE` in cli.py). The exact code is less important
    # than the fact that we're past secret loading and into the dry-run flow.
    assert run.exit_code != 0


@pytest.mark.parametrize(
    "bad_session_id",
    [
        "../../etc/passwd",  # path traversal
        "ses_../../../etc/passwd",  # path traversal masquerading as a session id
        "/absolute/path",  # absolute path
        "ses_SHORT",  # too short
        "ses_GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",  # non-hex
        "session_c94f353fc89d4eaca7c161c331ded65c",  # wrong prefix
        "",  # empty
        "ses_c94f353fc89d4eaca7c161c331ded65c\n",  # trailing newline
    ],
)
def test_cli_run_crm_resume_rejects_malformed_session_id(
    tmp_path: Path, bad_session_id: str
) -> None:
    """SECURITY (Copilot PR #9 round-3): `--resume <session-id>` MUST validate
    the operator-supplied id against the strict `ses_<32-hex>` shape BEFORE
    building any filesystem path from it. Without this validation, a crafted
    value containing path separators could cause the resume coordinator to
    read `<artifact_root>/<session_id>/writeback.json` outside the artifact
    root."""
    config_path = _write_config(tmp_path)
    run = _runner.invoke(
        app,
        [
            "run-crm",
            "--write",
            "--resume",
            bad_session_id,
            "--config",
            str(config_path),
        ],
    )
    assert run.exit_code == 2
    out = _combined_output(run)
    assert "not a valid session id" in out.lower()
