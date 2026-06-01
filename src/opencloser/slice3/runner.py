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

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from opencloser.artifacts.writer import (
    write_actual_writeback,
    write_planned_writeback,
    write_session_artifacts,
)
from opencloser.core import ids
from opencloser.core.clock import SystemClock
from opencloser.core.orchestrator import (
    _NEW_STATUS_MAP,
    _build_callback_task,
    _build_review_task,
    _format_transcript,
    _to_exported_decision,
)
from opencloser.crm.dataverse.adapter import DataverseWriteBackAdapter
from opencloser.eligibility.evaluator import BuiltinEligibilityEvaluator
from opencloser.models import (
    Disposition,
    NormalizedResult,
    PhoneCallActivityPayload,
    QueueStatusUpdatePayload,
    RunReport,
    Session,
    SessionState,
    Slice2Config,
    Slice3RunMode,
    SliceConfig,
    TaskPayload,
    WriteBackOperationStatus,
)
from opencloser.persona.alf_appointment_setter import ALFAppointmentSetterPersona
from opencloser.persona.base import SessionContext
from opencloser.runtime.pipecat.identity import build_runtime_identity
from opencloser.runtime.pipecat.provider import select_realtime_provider
from opencloser.slice2.runner import (
    CrmRunReport,
    _load_conversation_fixture,
    _load_dataverse_queue_item,
    _stage_queue_item,
    _verify_readiness,
)
from opencloser.slice3.run_report import build_run_report, write_run_report
from opencloser.state import store

# Dispositions that reached a connected live conversation and so warrant a
# Phone Call activity carrying the SignalWire-supplied connected-call
# timestamps. Terminal (non-connected) outcomes still update the queue row but
# MUST NOT record a false connected-call activity (SC-006, FR-006).
_TERMINAL_EVENT_DISPOSITION: Final[dict[str, Disposition]] = {
    "no_answer": Disposition.NO_ANSWER,
    "voicemail": Disposition.VOICEMAIL,
    "failed": Disposition.FAILED,
}

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
        "opencloser.slice3.runner.run_slice3 is the Typer-surface production "
        "entry point and remains a stub. The injectable orchestration cores are "
        "implemented — run_one_real_call covers BOTH the US1 real-call branch "
        "(T034) and the US2 rehearsal branch (T038, run_mode=REHEARSAL) and is "
        "exercised by the US1/US2 integration tests. What is still missing here "
        "is the production wiring: loading config/slice3.toml, building the "
        "Dataverse client + SQLite connection, mapping the run to an exit code, "
        "and the tolerant no-backing-store rehearsal path the test_cli_slice3 "
        "assertions drive. That wiring needs the Slice 3 config loader and the "
        "US3 telephony-readiness checker (T045/T046) and lands with US3."
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

    T034 implementation. The dependency-injectable core reuses the Slice 2
    readiness + queue-load helpers, drives the deterministic Slice 1 persona over
    the connected conversation (the live-model path never sets the disposition —
    FR-014), and assembles the Slice 3 write-back via
    :meth:`DataverseWriteBackAdapter.assemble_writeback` so ``do_not_call``
    finalizes DNC-first (Round 2 Q14). In this injectable seam the SignalWire
    dial is fixture-driven (the call-event transcript comes from
    ``transport_fixture`` and the provider call id is allocated locally); the
    production CLI path (:func:`run_slice3`) substitutes the real T026 transport.
    """
    clk = clock or SystemClock()
    persona = ALFAppointmentSetterPersona()

    # Rehearsal / readiness mode (FR-002, US2): verify readiness + eligibility and
    # produce the PLANNED write-back artifacts, but place zero SignalWire calls and
    # issue zero Dataverse create/update operations. The adapter and the metadata
    # verification both run in ``dry_run`` so every emit_* CAPTURES (never POSTs);
    # the local queue-status / attempt mutations that simulate the Dataverse state
    # are skipped, and the run report records ``run_mode = "rehearsal"`` with the
    # real provider call id left not-yet-assigned (SC-002, SC-011).
    is_rehearsal = run_mode is Slice3RunMode.REHEARSAL

    # ----- readiness + queue load (reuse the Slice 2 write-enabled gates) -----
    readiness = _verify_readiness(slice2_config, dataverse_client, clk, dry_run=is_rehearsal)
    if isinstance(readiness, CrmRunReport):
        return _blocked_before_call(readiness, run_mode=run_mode, operator_id=operator_id)
    translator = readiness.translator
    redaction_layer = readiness.redaction_layer

    loaded = _load_dataverse_queue_item(
        selector=selector,
        client=dataverse_client,
        translator=translator,
        slice2_config=slice2_config,
        metadata_report=readiness.metadata_report,
        clk=clk,
    )
    if isinstance(loaded, CrmRunReport):
        return _blocked_before_call(loaded, run_mode=run_mode, operator_id=operator_id)
    queue_item, _queue_baseline = loaded
    _stage_queue_item(conn, queue_item)

    # ----- eligibility gate (Slice 1 six rules, unchanged) -------------------
    decision = BuiltinEligibilityEvaluator().evaluate(queue_item, slice1_config, clk)

    session_id = ids.new_session_id()
    started_at = clk.now_utc_ms()
    # Provider call id (the SignalWire SID in production). Allocated locally in
    # this fixture-driven seam; surfaced as ``real_provider_call_id`` on the run
    # report and stamped onto the Phone Call activity (FR-006 / FR-020). In
    # rehearsal mode no dial is placed, so the SID is "not-yet-assigned": the
    # local correlation id is still allocated, but the run report and the planned
    # Phone Call activity carry ``None`` (US2 acceptance scenario #2).
    provider_call_id = ids.new_mock_provider_call_id()
    activity_provider_call_id = None if is_rehearsal else provider_call_id

    # ----- live call + deterministic disposition -----------------------------
    persona_output = None
    transcript_text: str | None = None
    connected = False
    connected_call_timestamps: dict[str, str] | None = None

    if decision.outcome == "block":
        disposition = Disposition.BLOCKED
    else:
        events = _read_transport_events(transport_fixture)
        connected = any(e.get("type") == "connected" for e in events)
        conversation = (
            _load_conversation_fixture(conversation_fixture)
            if connected and conversation_fixture is not None
            else None
        )
        if connected and conversation is not None:
            persona_output = persona.run(
                SessionContext(
                    session_id=session_id,
                    queue_item=queue_item,
                    mock_provider_call_id=provider_call_id,
                    started_at=started_at,
                    config=slice1_config,
                    clock=clk,
                ),
                conversation,
            )
            disposition = persona_output.final_disposition
            transcript_text = _format_transcript(conversation.turns)
            connected_call_timestamps = {
                "answered_at": _event_ts(events, "connected", started_at),
                "completed_at": _event_ts(events, "completed", clk.now_utc_ms()),
            }
        else:
            # No connected conversation: terminal disposition straight from the
            # call-event stream (no persona interaction). Never a connected-call
            # Phone Call activity.
            connected = False
            disposition = _terminal_disposition(events)

    ended_at = clk.now_utc_ms()
    persona_version = persona_output.persona_version if persona_output else persona.version

    normalized = _build_normalized(
        session_id=session_id,
        queue_item_id=queue_item.queue_item_id,
        provider_call_id=provider_call_id,
        persona_version=persona_version,
        disposition=disposition,
        persona_output=persona_output,
        connected=connected,
        blocked_reason=(decision.failing_rules if disposition is Disposition.BLOCKED else None),
        started_at=started_at,
        ended_at=ended_at,
    )

    # ----- persist the finalized session locally -----------------------------
    session = Session(
        session_id=session_id,
        queue_item_id=queue_item.queue_item_id,
        persona_version=persona_version if persona_output else None,
        state=SessionState.FINALIZED,
        final_disposition=disposition,
        blocked_reason=decision.failing_rules if disposition is Disposition.BLOCKED else None,
        mock_provider_call_id=provider_call_id,
        started_at=started_at,
        ended_at=ended_at,
    )
    with store.transaction(conn):
        store.insert_session(conn, session)
        store.insert_normalized_result(conn, normalized)
        # Rehearsal mode mutates zero CRM state, so the local queue-status mirror
        # and attempt counter (which simulate the Dataverse row) are left
        # untouched; only the local session + normalized-result audit rows are
        # persisted for inspection.
        if not is_rehearsal:
            store.update_queue_item_status(
                conn,
                queue_item.queue_item_id,
                last_decision_at=ended_at,
                callable_status=_NEW_STATUS_MAP.get(disposition, queue_item.callable_status),
                dnc_flag=True if disposition is Disposition.DO_NOT_CALL else None,
            )
            if decision.outcome != "block":
                store.increment_attempt_count(conn, queue_item.queue_item_id)

    # ----- Slice 3 write-back (DNC-first via assemble_writeback) -------------
    adapter = DataverseWriteBackAdapter(
        conn=conn,
        client=dataverse_client,
        translator=translator,
        task_owners=slice2_config.task_owners,
        now_utc_ms=clk.now_utc_ms,
        dry_run=is_rehearsal,
    )
    task_payload = _build_task_payload(
        disposition=disposition,
        session=session,
        queue_item=queue_item,
        normalized=normalized,
        persona_output=persona_output,
        ended_at=ended_at,
    )
    per_writeback = _emit_writeback(
        adapter,
        steps=adapter.assemble_writeback(normalized),
        conn=conn,
        session_id=session_id,
        queue_item=queue_item,
        disposition=disposition,
        persona_version=persona_version,
        provider_call_id=provider_call_id,
        real_provider_call_id=activity_provider_call_id,
        connected=connected,
        connected_call_timestamps=connected_call_timestamps,
        summary=normalized.summary or f"Final disposition: {disposition.value}",
        started_at=started_at,
        ended_at=ended_at,
        task_payload=task_payload,
        status="planned" if is_rehearsal else "completed",
    )

    # ----- artifacts + run report --------------------------------------------
    runtime_identity = _safe_runtime_identity()
    report = build_run_report(
        session_id=session_id,
        run_mode=run_mode,
        operator_current=operator_id,
        operator_original=None,
        real_provider_call_id=(
            None if is_rehearsal or decision.outcome == "block" else provider_call_id
        ),
        persona_version=persona_version,
        runtime_identity=runtime_identity if connected else None,
        final_disposition=disposition,
        human_review_reason=(persona_output.human_review_reason if persona_output else None),
        blocked_reason=(
            ",".join(decision.failing_rules)
            if disposition is Disposition.BLOCKED and decision.failing_rules
            else None
        ),
        per_writeback_operation_status=per_writeback,
        started_at=started_at,
        ended_at=ended_at,
    )

    writeback = adapter.build_writeback(session_id)
    paths = write_session_artifacts(
        artifact_root=slice1_config.artifacts.dir,
        session_id=session_id,
        normalized_result=normalized,
        writeback=writeback,
        eligibility_decision=_to_exported_decision(
            decision.model_copy(update={"session_id": session_id})
        ),
        task=task_payload,
        transcript_text=transcript_text,
        conflicting_events=None,
        redaction_layer=redaction_layer,
    )
    # Rehearsal mode emits the captured (dry-run) write-back as the planned
    # artifact an operator inspects before authorizing a real call (US2 T039);
    # a real-call run emits the actually-issued write-back as actual_writeback.json
    # so planned-vs-actual can be diffed (data-model §4, R4-Q43).
    if is_rehearsal:
        write_planned_writeback(
            artifact_root=slice1_config.artifacts.dir,
            session_id=session_id,
            writeback=writeback,
        )
    else:
        write_actual_writeback(
            artifact_root=slice1_config.artifacts.dir,
            session_id=session_id,
            writeback=writeback,
        )
    write_run_report(paths.session_dir, report)

    if is_rehearsal:
        exit_status = "rehearsed"
    elif disposition is Disposition.BLOCKED:
        exit_status = "blocked"
    else:
        exit_status = "completed"
    return RealCallRunReport(
        exit_status=exit_status,
        exit_code=EXIT_SUCCESS,
        session_id=session_id,
        final_disposition=disposition,
        artifact_dir=paths.session_dir,
        queue_item_id=queue_item.queue_item_id,
        run_mode=run_mode,
        run_report=report,
    )


# ---------------------------------------------------------------------------
# T034 helpers
# ---------------------------------------------------------------------------


def _read_transport_events(transport_fixture: Path) -> list[dict]:
    """Parse the fixture-driven call-event stream (Slice 1 transport-event shape)."""
    raw = json.loads(Path(transport_fixture).read_text(encoding="utf-8"))
    events = raw.get("events", [])
    return [e for e in events if isinstance(e, dict)]


def _event_ts(events: list[dict], event_type: str, fallback: str) -> str:
    for event in events:
        if event.get("type") == event_type and event.get("timestamp"):
            return str(event["timestamp"])
    return fallback


def _terminal_disposition(events: list[dict]) -> Disposition:
    for event in events:
        mapped = _TERMINAL_EVENT_DISPOSITION.get(str(event.get("type")))
        if mapped is not None:
            return mapped
    return Disposition.FAILED


def _build_normalized(
    *,
    session_id: str,
    queue_item_id: str,
    provider_call_id: str,
    persona_version: str,
    disposition: Disposition,
    persona_output,
    connected: bool,
    blocked_reason,
    started_at: str,
    ended_at: str,
) -> NormalizedResult:
    if persona_output is not None:
        ex = persona_output.extraction
        return NormalizedResult(
            session_id=session_id,
            queue_item_id=queue_item_id,
            mock_provider_call_id=provider_call_id,
            persona_version=persona_version,
            final_disposition=disposition,
            summary=(persona_output.summary or None) and persona_output.summary[:200],
            transcript_pointer="transcript.txt",
            captured_email=ex.captured_email,
            captured_email_unverified=ex.captured_email_unverified,
            callback_requested=ex.callback_requested,
            preferred_callback_window=ex.preferred_callback_window,
            human_review_reason=persona_output.human_review_reason,
            blocked_reason=None,
            started_at=started_at,
            ended_at=ended_at,
        )
    summary = (
        f"Blocked by eligibility: {','.join(blocked_reason)}."
        if disposition is Disposition.BLOCKED and blocked_reason
        else f"Disposition: {disposition.value}; no persona interaction."
    )
    return NormalizedResult(
        session_id=session_id,
        queue_item_id=queue_item_id,
        mock_provider_call_id=provider_call_id,
        persona_version=persona_version,
        final_disposition=disposition,
        summary=summary[:200],
        transcript_pointer=None,
        callback_requested=False,
        blocked_reason=blocked_reason,
        started_at=started_at,
        ended_at=ended_at,
    )


def _build_task_payload(
    *,
    disposition: Disposition,
    session: Session,
    queue_item,
    normalized: NormalizedResult,
    persona_output,
    ended_at: str,
) -> TaskPayload | None:
    if disposition in (
        Disposition.INTERESTED_CALLBACK_REQUESTED,
        Disposition.INTERESTED_EMAIL_CAPTURED,
        Disposition.CALL_BACK_LATER,
    ):
        return _build_callback_task(
            session=session, queue_item=queue_item, normalized=normalized, ended_at=ended_at
        )
    if disposition is Disposition.NEEDS_HUMAN_REVIEW:
        return _build_review_task(
            session=session,
            queue_item=queue_item,
            persona_output=persona_output,
            ended_at=ended_at,
        )
    return None


def _emit_writeback(
    adapter: DataverseWriteBackAdapter,
    *,
    steps,
    conn: sqlite3.Connection,
    session_id: str,
    queue_item,
    disposition: Disposition,
    persona_version: str,
    provider_call_id: str,
    real_provider_call_id: str | None,
    connected: bool,
    connected_call_timestamps: dict[str, str] | None,
    summary: str,
    started_at: str,
    ended_at: str,
    task_payload: TaskPayload | None,
    status: str = "completed",
) -> list[WriteBackOperationStatus]:
    """Emit each planned write-back step in ``assemble_writeback`` order.

    Returns the ``per_writeback_operation_status`` entries in emission order so
    the run report reflects DNC-first ordering (Round 2 Q14). A terminal
    (non-connected) outcome skips the Phone Call activity so no false
    connected-call record is written (SC-006).

    ``status`` is ``"completed"`` on a real-call run; rehearsal mode passes
    ``"planned"`` because the adapter ran in ``dry_run`` and captured (rather
    than issued) every operation (US2, FR-002).
    """
    emitted: list[WriteBackOperationStatus] = []
    for step in steps:
        if step.operation == "phone_call_activity":
            if not connected:
                continue
            activity = PhoneCallActivityPayload(
                session_id=session_id,
                queue_item_id=queue_item.queue_item_id,
                mock_provider_call_id=provider_call_id,
                persona_version=persona_version,
                final_disposition=disposition,
                summary=summary[:200],
                started_at=started_at,
                ended_at=ended_at,
            )
            with store.transaction(conn):
                adapter.emit_phone_call_activity(
                    activity,
                    provider_call_id=real_provider_call_id,
                    connected_call_timestamps=connected_call_timestamps,
                )
            emitted.append(WriteBackOperationStatus(operation="phone_call_activity", status=status))
        elif step.variant is not None:
            new_status = _NEW_STATUS_MAP.get(disposition, queue_item.callable_status)
            payload = QueueStatusUpdatePayload(
                session_id=session_id,
                queue_item_id=queue_item.queue_item_id,
                previous_status=queue_item.callable_status,
                new_status=new_status,
                transition_reason=disposition.value,
                transition_at=ended_at,
            )
            with store.transaction(conn):
                adapter.emit_queue_status_update(payload, variant=step.variant)
            emitted.append(WriteBackOperationStatus(operation=step.operation, status=status))
        elif step.operation == "task" and task_payload is not None:
            with store.transaction(conn):
                adapter.emit_task(task_payload)
            emitted.append(WriteBackOperationStatus(operation="task", status=status))
    return emitted


def _safe_runtime_identity():
    """Record the runtime/model identity (FR-016); never fails the run."""
    try:
        return build_runtime_identity(select_realtime_provider())
    except (ValueError, RuntimeError):  # pragma: no cover - defensive
        return None


def _blocked_before_call(
    crm_report: CrmRunReport, *, run_mode: Slice3RunMode, operator_id: str
) -> RealCallRunReport:
    """Map a Slice 2 readiness / queue-load short-circuit to a Slice 3 exit."""
    exit_code = EXIT_DATAVERSE_UNREACHABLE if crm_report.exit_status == "blocked" else EXIT_SUCCESS
    return RealCallRunReport(
        exit_status=crm_report.exit_status,
        exit_code=exit_code,
        session_id=crm_report.session_id,
        queue_item_id=crm_report.queue_item_id,
        run_mode=run_mode,
        warnings=[crm_report.message] if crm_report.message else [],
    )
