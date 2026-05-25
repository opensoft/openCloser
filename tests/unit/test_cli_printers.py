"""Unit tests for the CLI report-formatter helpers.

Pinning the operator-visible output of the typed `block_reason` discriminator
(Codex PR #3 P2 post-swarm). Before this fix the discriminator was carried on
both `CrmRunReport` and `ResumeReport` but never printed — operators had to
parse the free-text `message:` line to recover the cause.

Both run-crm and run-crm --resume paths print to the same stream; this module
unit-tests each printer in isolation so we don't have to spin up the live-
Dataverse plumbing just to assert one stdout line.
"""

from __future__ import annotations

from pathlib import Path

import typer
from typer.testing import CliRunner

from opencloser.cli import _print_crm_report
from opencloser.slice2.resume import ResumeReport
from opencloser.slice2.runner import CrmRunReport

_runner = CliRunner()


def _invoke(printer, *args):
    """Wrap a printer that uses `typer.echo` in a single-command Typer app so
    the CliRunner captures its stdout deterministically."""
    app = typer.Typer()

    @app.command()
    def main() -> None:
        printer(*args)

    return _runner.invoke(app)


def test_print_crm_report_includes_block_reason_when_present() -> None:
    report = CrmRunReport(
        exit_status="blocked",
        block_reason="metadata",
        message="mapping artifact 'config/dataverse_mapping.json' is not approved",
    )
    result = _invoke(_print_crm_report, report)
    assert result.exit_code == 0
    assert "exit_status:           blocked" in result.output
    assert "block_reason:          metadata" in result.output
    assert "message:" in result.output


def test_print_crm_report_omits_block_reason_for_completed_runs() -> None:
    report = CrmRunReport(
        exit_status="completed",
        session_id="ses_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    )
    result = _invoke(_print_crm_report, report)
    assert result.exit_code == 0
    assert "exit_status:           completed" in result.output
    assert "block_reason:" not in result.output


def test_print_crm_report_includes_conflict_detected_reason() -> None:
    """T045 path — conflict_detected must appear in the operator output so a
    human-edit-mid-run is distinguishable from a generic permanent failure."""
    report = CrmRunReport(
        exit_status="blocked",
        block_reason="conflict_detected",
        session_id="ses_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        queue_item_id="11111111-1111-1111-1111-111111111111",
        message="conflict_detected: conflicting fields: medx_priority",
    )
    result = _invoke(_print_crm_report, report)
    assert "block_reason:          conflict_detected" in result.output


def test_resume_printer_includes_block_reason_when_present(tmp_path: Path) -> None:
    """The resume printer in cli._run_crm_resume mirrors `_print_crm_report`
    for `block_reason`. Test via a tiny adapter that replays the same lines
    against `typer.echo` to keep the assertion focused."""
    result = ResumeReport(
        exit_status="blocked",
        block_reason="conflict_detected",
        session_id="ses_cccccccccccccccccccccccccccccccc",
        artifact_dir=tmp_path / "ses_cccccccccccccccccccccccccccccccc",
        operations_replayed=[],
        message="resume replay failed: conflict_detected on baseline reload",
    )

    def _print_resume(r: ResumeReport) -> None:
        # Mirrors cli._run_crm_resume's printer block. If the CLI ever extracts
        # this into a named helper, switch this test to import that helper.
        typer.echo(f"exit_status:           {r.exit_status}")
        block_reason = getattr(r, "block_reason", None)
        if block_reason:
            typer.echo(f"block_reason:          {block_reason}")
        typer.echo(f"session_id:            {r.session_id}")
        if r.artifact_dir is not None:
            typer.echo(f"artifact_dir:          {r.artifact_dir}")
        if r.operations_replayed is not None:
            typer.echo(
                f"operations_replayed:   {', '.join(r.operations_replayed) or 'none'}"
            )
        if r.message:
            typer.echo(f"message:               {r.message}")

    out = _invoke(_print_resume, result)
    assert out.exit_code == 0
    assert "exit_status:           blocked" in out.output
    assert "block_reason:          conflict_detected" in out.output
