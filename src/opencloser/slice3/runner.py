"""Slice 3 — Real Call, Real CRM — orchestrator runner (foundational skeleton).

Public entry point: :func:`run_slice3`. Wired from ``opencloser.cli`` by the
``opencloser run3`` Typer subcommand (T012).

Implementation policy (T011 foundational scope):

- This module exposes the public callable shape and the exit-code contract per
  ``specs/003-real-call-real-crm/contracts/cli-slice3.md``. The end-to-end
  orchestration logic (claim → readiness → dial → conversation → finalize →
  write-back) lands in **US1 (T034)**.
- Rehearsal-mode (US2) and the per-readiness-category gates (US3) land in
  their own user-story phases.
- Resume coordination (US4 Q6 + US7 Q12 + US7 Q13) lands in
  ``opencloser.slice3.resume`` (US4 T057 + US7 T087-T088).
- Post-finalization grace window (US6 Q7) lands in
  ``opencloser.slice3.grace_window`` (US6 T077).
- Telephony readiness (FR-009 — FR-012) lands in
  ``opencloser.slice3.readiness`` (US3 T045).
- Run-report builder (FR-036) lands in ``opencloser.slice3.run_report`` (US1 T033).

Until those user-story tasks land, ``run_slice3`` raises
:class:`NotImplementedError` with a clear message naming the next required
task. This is intentional: the foundational scope establishes the public
boundary the CLI imports against, without committing to any behavior the
user-story tasks own.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from opencloser.models import (
    Disposition,
    RunReport,
    Slice2Config,
    Slice3RunMode,
    SliceConfig,
)

# Slice 3 CLI exit codes (contracts/cli-slice3.md §"Exit codes"). Owned here so
# the CLI surface and the runner surface cannot drift apart.
EXIT_SUCCESS: Final[int] = 0
EXIT_UNEXPECTED: Final[int] = 1
EXIT_BAD_CLI_USAGE: Final[int] = 2
EXIT_CONCURRENT_CLAIM: Final[int] = 3
EXIT_TELEPHONY_READINESS_FAILURE: Final[int] = 4
EXIT_PROVIDER_REJECTED_DIAL: Final[int] = 5
EXIT_LIVE_CALL_ABANDONMENT: Final[int] = 6
EXIT_DATAVERSE_UNREACHABLE: Final[int] = 7


@dataclass(frozen=True, slots=True)
class Slice3Args:
    """Parsed CLI arguments passed from ``opencloser.cli`` to :func:`run_slice3`.

    Mirrors the option set documented in contracts/cli-slice3.md. The CLI
    parser (``opencloser.cli`` T012) constructs an instance and forwards it
    here. Keeping a typed value object at the boundary lets the runner stay
    Typer-agnostic.
    """

    campaign_id: str
    queue_item_id: str
    run_mode: Slice3RunMode
    shadow_stt_enabled: bool | None  # None = use config default
    operator_id: str
    resume_session_id: str | None
    config_path: str | None


def run_slice3(args: Slice3Args) -> int:
    """Process exactly one Dataverse queue item per invocation (FR-003).

    Returns the numeric exit code per the Slice 3 CLI contract. The CLI
    forwards the return value to ``typer.Exit`` so non-zero exit codes surface
    to the shell.

    Foundational status (T011): the public callable shape is stable. End-to-end
    behavior is wired in US1 (T034); rehearsal-only behavior in US2 (T038);
    readiness gates in US3 (T046); idempotent callback handling in US4 (T055 —
    T057); persona safety in US5 (T065 — T067); shadow STT in US6 (T078); and
    recovery in US7 (T087 — T089).
    """
    raise NotImplementedError(
        "opencloser.slice3.runner.run_slice3 is a Phase-2 foundational stub. "
        "The end-to-end real-call branch lands in US1 task T034 "
        "(see specs/003-real-call-real-crm/tasks.md); the rehearsal-mode "
        "branch lands in US2 task T038. Run the CLI in rehearsal mode by "
        "omitting --real-call once those tasks complete."
    )


@dataclass(frozen=True, slots=True)
class RealCallRunReport:
    """Exit report from a single Slice 3 real-call run.

    The dependency-injectable analogue of the Slice 2
    :class:`opencloser.slice2.runner.CrmRunReport`. Returned by
    :func:`run_one_real_call` so integration tests (US1 T017-T021) can assert on
    the final disposition, the on-disk artifact directory, and the FR-036
    :class:`~opencloser.models.RunReport` without driving the Typer CLI surface.

    Populated by the US1 runner (T034). The field set is the observable contract
    the US1 integration tests pin; do not narrow it without updating those tests.
    """

    exit_status: str
    exit_code: int
    session_id: str | None = None
    final_disposition: Disposition | None = None
    artifact_dir: Path | None = None
    queue_item_id: str | None = None
    run_mode: Slice3RunMode = Slice3RunMode.REAL_CALL
    run_report: RunReport | None = None
    warnings: list[str] = field(default_factory=list)


def run_one_real_call(
    selector: object,
    *,
    transport_fixture: Path,
    conversation_fixture: Path | None,
    slice1_config: SliceConfig,
    slice2_config: Slice2Config,
    dataverse_client: object,
    conn: sqlite3.Connection,
    campaign_id: str,
    operator_id: str,
    run_mode: Slice3RunMode = Slice3RunMode.REAL_CALL,
    clock: object | None = None,
    resume_session_id: str | None = None,
) -> RealCallRunReport:
    """Execute exactly one Slice 3 real-call run end-to-end against injected fakes.

    The dependency-injectable core that the ``opencloser run3`` CLI
    (:func:`run_slice3`) wraps with config-loaded, production dependencies. The
    integration tests inject an in-process Dataverse fake (``dataverse_client``)
    plus fixture-driven SignalWire transport and real-time-AI runtime fakes
    (built internally from ``transport_fixture`` / ``conversation_fixture``,
    exactly as the Slice 2 runner builds its fixture-driven mock transport).

    Parameters mirror :func:`opencloser.slice2.runner.run_one_crm_item` plus the
    Slice 3 additions: ``run_mode`` (rehearsal vs real-call dial+mutation gate
    per FR-001 / FR-002), ``operator_id`` + ``resume_session_id`` (operator
    identity preservation per Round 2 Q12), and ``campaign_id``.

    Foundational status (T011): this is a stub. The real-call orchestration —
    claim -> readiness -> dial (T026) -> bridge audio (T030) -> deterministic
    disposition -> CRM write-back (T031) -> artifacts (T032) -> run report
    (T033) -> :class:`RealCallRunReport` — lands in **US1 task T034**.
    """
    raise NotImplementedError(
        "opencloser.slice3.runner.run_one_real_call is a Phase-2 foundational "
        "stub. The end-to-end real-call orchestration (claim -> readiness -> "
        "dial -> bridge audio -> deterministic disposition -> CRM write-back -> "
        "artifacts -> run report) lands in US1 task T034 "
        "(see specs/003-real-call-real-crm/tasks.md)."
    )
