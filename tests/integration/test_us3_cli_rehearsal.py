"""T119 — `run_slice3` tolerant config-only rehearsal (R4-Q38).

`opencloser run3` (no `--real-call`) loads config/slice3.toml, runs the
config-level telephony readiness checks, writes `telephony_readiness.json` + a
`run_mode="rehearsal"` run report, and exits 0 — surfacing the Dataverse gaps as
readiness fails rather than silently passing or dialing blind.

The full FR-036 run report is asserted here (the `test_cli_slice3` contract
tests cannot, because they point at an unconfigurable artifacts dir); this test
controls the CWD so the default `artifacts/` lands in a temp dir.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from opencloser.models import Slice3RunMode
from opencloser.slice3.runner import EXIT_SUCCESS, Slice3Args, run_slice3

pytestmark = pytest.mark.integration

_SLICE3_TOML = """\
[signalwire]
source_caller_id = "+15555550100"
status_callback_url_template = "https://cb.example.com/sw/status/{session_id}"
media_callback_url_template = "https://cb.example.com/sw/media/{session_id}"

[shadow_stt]
enabled_default = false
"""

_REQUIRED_FR036_FIELDS = (
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
    "started_at",
)


def test_run_slice3_rehearsal_exits_0_with_run_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A config-only rehearsal exits 0 and writes a complete run report +
    telephony_readiness.json, with the Dataverse-dependent checks surfaced as
    fails."""
    config = tmp_path / "slice3.toml"
    config.write_text(_SLICE3_TOML, encoding="utf-8")
    monkeypatch.chdir(tmp_path)  # default `artifacts/` lands under tmp_path

    args = Slice3Args(
        campaign_id="alf-q2",
        queue_item_id="alf-prospect-cli",
        run_mode=Slice3RunMode.REHEARSAL,
        shadow_stt_enabled=None,
        operator_id="operator-cli",
        resume_session_id=None,
        config_path=str(config),
    )

    code = run_slice3(args)
    assert code == EXIT_SUCCESS, "config-only rehearsal must exit 0 (R4-Q38)"

    reports = list((tmp_path / "artifacts").rglob("run_report.json"))
    assert reports, "rehearsal must write a run_report.json"
    report = json.loads(reports[0].read_text(encoding="utf-8"))

    assert report["run_mode"] == Slice3RunMode.REHEARSAL.value
    assert report["real_provider_call_id"] is None
    missing = [f for f in _REQUIRED_FR036_FIELDS if f not in report]
    assert not missing, f"run report missing FR-036 fields: {missing}"

    # The readiness report is present and surfaces the config-checkable results.
    readiness = list((tmp_path / "artifacts").rglob("telephony_readiness.json"))
    assert readiness, "rehearsal must write telephony_readiness.json"
    checks = {c["check_name"]: c["result"] for c in report["telephony_readiness_summary"]}
    # Config-present checks pass; queue/Dataverse-dependent checks surface as fail.
    assert checks["source_caller_id_authorized"] == "pass"
    assert checks["status_callback_url_configured"] == "pass"
    assert checks["destination_phone_e164"] == "fail"  # no queue item loaded
    assert checks["dataverse_metadata_verified"] == "fail"


def test_run_slice3_no_secrets_in_run_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SC-018: a credential set in the environment never appears in the run
    report produced by a rehearsal."""
    secret = "T119-SIGNALWIRE-SECRET-must-not-appear"
    monkeypatch.setenv("SIGNALWIRE_SIGNING_SECRET", secret)
    config = tmp_path / "slice3.toml"
    config.write_text(_SLICE3_TOML, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    args = Slice3Args(
        campaign_id="alf-q2",
        queue_item_id="alf-prospect-cli",
        run_mode=Slice3RunMode.REHEARSAL,
        shadow_stt_enabled=None,
        operator_id="operator-cli",
        resume_session_id=None,
        config_path=str(config),
    )
    assert run_slice3(args) == EXIT_SUCCESS

    for path in (tmp_path / "artifacts").rglob("*"):
        if path.is_file():
            assert secret not in path.read_text(encoding="utf-8"), f"secret leaked into {path}"
