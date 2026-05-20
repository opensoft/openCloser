"""Interaction Core / Orchestrator — FR-033 module boundary #5.

Wires Eligibility → Transport → Persona → CRM Write-back → Artifacts into a single
deterministic loop. Owns session lifecycle, idempotency (FR-019), attempt-count
increments (FR-021), and the conflicting-late-event audit channel (FR-020).

Contract: see specs/001-mock-call-mock-crm/contracts/orchestrator.md
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from opencloser.artifacts.writer import ArtifactPaths, write_session_artifacts
from opencloser.core import ids, idempotency
from opencloser.core.clock import Clock, SystemClock
from opencloser.crm.mock import MockWriteBackAdapter
from opencloser.models import (
    CallableStatus,
    ConflictingEventAuditRecord,
    Disposition,
    EventType,
    ExportedEligibilityDecision,
    MockCallEvent,
    NormalizedResult,
    PhoneCallActivityPayload,
    QueueStatusUpdatePayload,
    RuleCode,
    Session,
    SessionState,
    SliceConfig,
    TaskPayload,
    WriteBackKind,
)
from opencloser.persona.alf_appointment_setter import ALFAppointmentSetterPersona
from opencloser.persona.base import (
    ConversationFixture,
    ConversationTurn,
    PersonaOutput,
    SessionContext,
)
from opencloser.state import store

if TYPE_CHECKING:
    from opencloser.eligibility.evaluator import BuiltinEligibilityEvaluator
    from opencloser.transport.mock import FixtureDrivenTransport


# Terminal events that finalize a session.
_TERMINAL_EVENTS: frozenset[EventType] = frozenset(
    {EventType.NO_ANSWER, EventType.VOICEMAIL, EventType.FAILED, EventType.COMPLETED}
)

# FR-031 per-disposition write-back emission map.
_EMITS_PHONE_CALL_ACTIVITY: frozenset[Disposition] = frozenset(
    Disposition.__members__.values()
) - {Disposition.BLOCKED}

_EMITS_CALLBACK_TASK: frozenset[Disposition] = frozenset(
    {
        Disposition.INTERESTED_CALLBACK_REQUESTED,
        Disposition.INTERESTED_EMAIL_CAPTURED,
        Disposition.CALL_BACK_LATER,
    }
)
_EMITS_REVIEW_TASK: frozenset[Disposition] = frozenset({Disposition.NEEDS_HUMAN_REVIEW})

# FR-032 per-disposition new_status mapping.
_NEW_STATUS_MAP: dict[Disposition, CallableStatus] = {
    Disposition.INTERESTED_CALLBACK_REQUESTED: CallableStatus.READY,
    Disposition.INTERESTED_EMAIL_CAPTURED: CallableStatus.COMPLETED,
    Disposition.CALL_BACK_LATER: CallableStatus.READY,
    Disposition.NOT_INTERESTED: CallableStatus.COMPLETED,
    Disposition.WRONG_NUMBER: CallableStatus.BLOCKED,
    Disposition.NO_ANSWER: CallableStatus.READY,
    Disposition.VOICEMAIL: CallableStatus.READY,
    Disposition.DO_NOT_CALL: CallableStatus.DNC,
    Disposition.NEEDS_HUMAN_REVIEW: CallableStatus.BLOCKED,
    Disposition.FAILED: CallableStatus.READY,
    # BLOCKED is handled specially: new_status = previous_status (no transition).
}


@dataclass(frozen=True, slots=True)
class RunReport:
    """Returned to the CLI; not exported as JSON."""

    session_id: str
    final_disposition: Disposition
    mock_provider_call_id: str | None
    artifact_dir: Path
    wall_time_ms: int
    eligibility_outcome: str  # "allow" | "block"


class QueueItemNotFound(Exception):
    """The requested queue_item_id is not present in local state."""


def process_one_queue_item(
    queue_item_id: str,
    *,
    conn: sqlite3.Connection,
    config: SliceConfig,
    eligibility: "BuiltinEligibilityEvaluator",
    transport: "FixtureDrivenTransport",
    persona: ALFAppointmentSetterPersona,
    conversation_fixture: ConversationFixture | None,
    transport_fixture_id: str | None,
    clock: Clock | None = None,
) -> RunReport:
    """End-to-end Slice 1 orchestration for a single queue record.

    Block path: handles eligibility=block per FR-005 + Q3 always-create-session.
    Allow path: places mock call, processes events, runs persona on `connected`, emits
    write-back payloads per FR-031, and exports all artifacts.

    `conversation_fixture` is required when a call is expected to reach `connected`.
    `transport_fixture_id` is the name of the fixture under the transport's fixtures dir.
    """
    clock = clock or SystemClock()
    start_ts_monotonic = time.monotonic()

    # ----- step 1: load queue item ------------------------------------------
    queue_item = store.get_queue_item(conn, queue_item_id)
    if queue_item is None:
        raise QueueItemNotFound(queue_item_id)

    # ----- step 2: eligibility decision -------------------------------------
    decision = eligibility.evaluate(queue_item, config, clock)

    # Pre-validate allow-path inputs BEFORE creating any session row, so a bad
    # invocation never leaves a partial session behind (P1-5 / N3).
    if decision.outcome != "block" and transport_fixture_id is None:
        raise ValueError("transport_fixture_id is required when eligibility allows the call")

    # ----- step 3: create session row (always, per Q3) ----------------------
    session_id = ids.new_session_id()
    started_at = clock.now_utc_ms()
    initial_state = SessionState.BLOCKED if decision.outcome == "block" else SessionState.CREATED
    final_disp_at_start = Disposition.BLOCKED if decision.outcome == "block" else None
    blocked_reason: list[RuleCode] | None = decision.failing_rules if decision.outcome == "block" else None
    initial_session = Session(
        session_id=session_id,
        queue_item_id=queue_item.queue_item_id,
        persona_version=None,
        state=initial_state,
        final_disposition=final_disp_at_start,
        blocked_reason=blocked_reason,
        mock_provider_call_id=None,
        started_at=started_at,
        ended_at=started_at if decision.outcome == "block" else None,
    )
    with store.transaction(conn):
        store.insert_session(conn, initial_session)
        # Backfill session_id on the decision and persist.
        decision_with_session = decision.model_copy(update={"session_id": session_id})
        store.insert_eligibility_decision(conn, decision_with_session)
        store.update_queue_item_status(
            conn, queue_item_id, last_decision_at=clock.now_utc_ms()
        )

    # ----- block branch -----------------------------------------------------
    if decision.outcome == "block":
        report = _finalize_blocked(
            conn=conn,
            session=initial_session,
            queue_item=queue_item,
            decision=decision_with_session,
            config=config,
            clock=clock,
            start_ts_monotonic=start_ts_monotonic,
        )
        return report

    # ----- allow branch -----------------------------------------------------
    return _run_allowed_session(
        conn=conn,
        session=initial_session,
        queue_item=queue_item,
        decision=decision_with_session,
        config=config,
        clock=clock,
        eligibility=eligibility,
        transport=transport,
        persona=persona,
        conversation_fixture=conversation_fixture,
        transport_fixture_id=transport_fixture_id,
        start_ts_monotonic=start_ts_monotonic,
    )


# ---------------------------------------------------------------------------
# Block branch
# ---------------------------------------------------------------------------


def _finalize_blocked(
    *,
    conn: sqlite3.Connection,
    session: Session,
    queue_item,
    decision,
    config: SliceConfig,
    clock: Clock,
    start_ts_monotonic: float,
) -> RunReport:
    """FR-005 block path: queue-status update only, no Phone Call activity, no task."""
    crm = MockWriteBackAdapter(conn)
    new_status = queue_item.callable_status  # FR-032: blocked → unchanged
    failing_str = ",".join(decision.failing_rules) if decision.failing_rules else ""
    status_payload = QueueStatusUpdatePayload(
        session_id=session.session_id,
        queue_item_id=queue_item.queue_item_id,
        previous_status=queue_item.callable_status,
        new_status=new_status,
        transition_reason=f"blocked_by_eligibility: {failing_str}",
        transition_at=clock.now_utc_ms(),
    )
    key = idempotency.compute_key(
        session_id=session.session_id,
        mock_provider_call_id=None,
        event_id=None,
        write_back_kind=WriteBackKind.QUEUE_STATUS_UPDATE,
    )
    with store.transaction(conn):
        if idempotency.record_or_skip(conn, key, applied_at=clock.now_utc_ms()):
            crm.emit_queue_status_update(status_payload)

    writeback = crm.build_writeback(session.session_id)

    normalized = NormalizedResult(
        session_id=session.session_id,
        queue_item_id=queue_item.queue_item_id,
        mock_provider_call_id=None,
        persona_version=None,
        final_disposition=Disposition.BLOCKED,
        summary=f"Blocked by eligibility: {failing_str}.",
        transcript_pointer=None,
        callback_requested=False,
        blocked_reason=decision.failing_rules,
        started_at=session.started_at,
        ended_at=session.ended_at or session.started_at,
    )
    with store.transaction(conn):
        store.insert_normalized_result(conn, normalized)

    paths = write_session_artifacts(
        artifact_root=config.artifacts.dir,
        session_id=session.session_id,
        normalized_result=normalized,
        writeback=writeback,
        eligibility_decision=_to_exported_decision(decision),
        task=None,
        transcript_text=None,
        conflicting_events=None,
    )

    return RunReport(
        session_id=session.session_id,
        final_disposition=Disposition.BLOCKED,
        mock_provider_call_id=None,
        artifact_dir=paths.session_dir,
        wall_time_ms=int((time.monotonic() - start_ts_monotonic) * 1000),
        eligibility_outcome="block",
    )


# ---------------------------------------------------------------------------
# Allowed branch — happy + alternate paths
# ---------------------------------------------------------------------------


def _run_allowed_session(
    *,
    conn: sqlite3.Connection,
    session: Session,
    queue_item,
    decision,
    config: SliceConfig,
    clock: Clock,
    eligibility,
    transport: "FixtureDrivenTransport",
    persona: ALFAppointmentSetterPersona,
    conversation_fixture: ConversationFixture | None,
    transport_fixture_id: str | None,
    start_ts_monotonic: float,
) -> RunReport:
    del eligibility  # already used; kept for signature symmetry

    # transport_fixture_id is pre-validated by process_one_queue_item (P1-5) before
    # the session row is created — by here it is guaranteed present.
    assert transport_fixture_id is not None

    # Transition session to eligibility_evaluated.
    with store.transaction(conn):
        store.update_session(conn, session.session_id, state=SessionState.ELIGIBILITY_EVALUATED)

    # Place call.
    mock_call_id = transport.place_call(queue_item, transport_fixture_id)
    with store.transaction(conn):
        store.update_session(
            conn,
            session.session_id,
            mock_provider_call_id=mock_call_id,
            state=SessionState.IN_FLIGHT,
        )

    # Increment attempt count exactly once for this mock_provider_call_id (FR-021).
    attempt_key = idempotency.compute_key(
        session_id=session.session_id,
        mock_provider_call_id=mock_call_id,
        event_id=None,
        write_back_kind=WriteBackKind.ATTEMPT_COUNT,
    )
    with store.transaction(conn):
        if idempotency.record_or_skip(conn, attempt_key, applied_at=clock.now_utc_ms()):
            store.increment_attempt_count(conn, queue_item.queue_item_id)

    # Drain the FULL transport event stream. The session is finalized once, AFTER the
    # loop — keeping iteration going past the first terminal event is what lets FR-020
    # conflicting late events be audited instead of silently dropped (C1).
    persona_output: PersonaOutput | None = None
    transcript_text: str | None = None
    finalizing_event: MockCallEvent | None = None
    final_disposition: Disposition | None = None
    conflicting_events: list[ConflictingEventAuditRecord] = []

    for raw_event in transport.event_stream(mock_call_id):
        # Re-key the event to the session_id (transport returned events scoped by call_id).
        event = MockCallEvent(
            session_id=session.session_id,
            event_id=raw_event.event_id,
            event_type=raw_event.event_type,
            received_at=raw_event.received_at,
            payload=raw_event.payload,
        )

        event_key = idempotency.compute_key(
            session_id=session.session_id,
            mock_provider_call_id=mock_call_id,
            event_id=event.event_id,
            write_back_kind=WriteBackKind.SESSION_STATE,
        )

        # Idempotency-key INSERT and the state mutation it gates run in ONE transaction
        # (H1) — a crash can never record the key without persisting the event/audit row.
        with store.transaction(conn):
            # Duplicate detection (FR-019). A UNIQUE violation on idempotency_keys means
            # this event was already applied — silent no-op, even if it is also a
            # conflicting late event (FR-019 wins over FR-020 per the clarifications).
            if not idempotency.record_or_skip(conn, event_key, applied_at=clock.now_utc_ms()):
                continue

            # Conflicting late event (FR-020): the session already had a finalizing
            # event this run. A late terminal event is audit-logged (separate channel);
            # it does NOT mutate state or emit write-backs. Non-terminal late events
            # (e.g. a stray callback_requested) are simply dropped.
            if finalizing_event is not None:
                if event.event_type in _TERMINAL_EVENTS:
                    audit = ConflictingEventAuditRecord(
                        audit_id=ids.new_audit_id(),
                        session_id=session.session_id,
                        event_id=event.event_id,
                        conflicting_event_type=event.event_type,
                        received_at=event.received_at,
                        full_event_payload=event.payload,
                        preserved_disposition=final_disposition or Disposition.FAILED,
                    )
                    conflicting_events.append(audit)
                    store.insert_conflicting_event(conn, audit)
                continue

            # Normal path: persist the event row atomically with its idempotency key.
            store.insert_mock_call_event(conn, event)

        # On `connected`: run the persona over the full conversation fixture (once).
        if event.event_type is EventType.CONNECTED and persona_output is None:
            if conversation_fixture is not None:
                session_context = SessionContext(
                    session_id=session.session_id,
                    queue_item=queue_item,
                    mock_provider_call_id=mock_call_id,
                    started_at=session.started_at,
                    config=config,
                    clock=clock,
                )
                persona_output = persona.run(session_context, conversation_fixture)
                transcript_text = _format_transcript(conversation_fixture.turns)
                with store.transaction(conn):
                    store.update_session(
                        conn,
                        session.session_id,
                        persona_version=persona_output.persona_version,
                    )
            # else: no conversation fixture supplied for a connected call — the persona
            # cannot run; the session finalizes cleanly as `failed` (P1-5) rather than
            # raising mid-stream.

        # First terminal event marks the finalization point. We record it and the
        # resolved disposition, but keep draining the stream so later events that
        # arrive after finalization are routed to the FR-020 audit channel above.
        if finalizing_event is None and event.event_type in _TERMINAL_EVENTS:
            finalizing_event = event
            final_disposition = _resolve_final_disposition(event, persona_output)

    # Stream fully drained. Resolve the disposition (covers the no-terminal-event case,
    # e.g. only callback_requested or a truncated fixture) and finalize exactly once.
    if final_disposition is None:
        final_disposition = _resolve_final_disposition(finalizing_event, persona_output)

    normalized, paths = _finalize_session(
        conn=conn,
        session=session,
        queue_item=queue_item,
        decision=decision,
        config=config,
        clock=clock,
        mock_call_id=mock_call_id,
        disposition=final_disposition,
        persona_output=persona_output,
        transcript_text=transcript_text,
        conflicting_events=conflicting_events,
    )
    return RunReport(
        session_id=session.session_id,
        final_disposition=final_disposition,
        mock_provider_call_id=mock_call_id,
        artifact_dir=paths.session_dir,
        wall_time_ms=int((time.monotonic() - start_ts_monotonic) * 1000),
        eligibility_outcome="allow",
    )


def _resolve_final_disposition(
    finalizing_event: MockCallEvent | None,
    persona_output: PersonaOutput | None,
) -> Disposition:
    """Map the finalizing event + persona output to a final disposition."""
    if finalizing_event is None:
        return persona_output.final_disposition if persona_output else Disposition.FAILED
    et = finalizing_event.event_type
    if et is EventType.COMPLETED and persona_output is not None:
        # Conversation completed cleanly — persona's disposition wins.
        return persona_output.final_disposition
    if et is EventType.NO_ANSWER:
        return Disposition.NO_ANSWER
    if et is EventType.VOICEMAIL:
        return Disposition.VOICEMAIL
    if et is EventType.FAILED:
        return Disposition.FAILED
    if et is EventType.COMPLETED:
        return persona_output.final_disposition if persona_output else Disposition.FAILED
    return Disposition.FAILED


def _finalize_session(
    *,
    conn: sqlite3.Connection,
    session: Session,
    queue_item,
    decision,
    config: SliceConfig,
    clock: Clock,
    mock_call_id: str,
    disposition: Disposition,
    persona_output: PersonaOutput | None,
    transcript_text: str | None,
    conflicting_events: list[ConflictingEventAuditRecord],
) -> tuple[NormalizedResult, ArtifactPaths]:
    """Finalize the session, emit write-backs per FR-031, write artifacts."""
    ended_at = clock.now_utc_ms()

    # Build NormalizedResult.
    normalized = _build_normalized_result(
        session=session,
        queue_item=queue_item,
        mock_call_id=mock_call_id,
        disposition=disposition,
        persona_output=persona_output,
        ended_at=ended_at,
    )

    # Persist the disposition, normalized result, and queue-item lifecycle update.
    # The session's `state` is intentionally NOT flipped to FINALIZED here — that
    # flip is the LAST commit, after write-backs and artifacts succeed (N3), so a
    # FINALIZED session row is guaranteed to have its write-backs and artifacts.
    with store.transaction(conn):
        store.update_session(
            conn,
            session.session_id,
            final_disposition=disposition,
            ended_at=ended_at,
        )
        store.insert_normalized_result(conn, normalized)
        store.update_queue_item_status(
            conn,
            queue_item.queue_item_id,
            last_decision_at=ended_at,
            callable_status=_NEW_STATUS_MAP.get(disposition, queue_item.callable_status),
            dnc_flag=True if disposition is Disposition.DO_NOT_CALL else None,
        )

    # Emit write-backs per FR-031.
    crm = MockWriteBackAdapter(conn)
    activity: PhoneCallActivityPayload | None = None
    if disposition in _EMITS_PHONE_CALL_ACTIVITY:
        activity = PhoneCallActivityPayload(
            session_id=session.session_id,
            queue_item_id=queue_item.queue_item_id,
            mock_provider_call_id=mock_call_id,
            persona_version=(persona_output.persona_version if persona_output else "alf-appointment-setter@0.1.0"),
            final_disposition=disposition,
            summary=(normalized.summary or f"Final disposition: {disposition.value}")[:200],
            started_at=session.started_at,
            ended_at=ended_at,
        )
        activity_key = idempotency.compute_key(
            session_id=session.session_id,
            mock_provider_call_id=mock_call_id,
            event_id=None,
            write_back_kind=WriteBackKind.PHONE_CALL_ACTIVITY,
        )
        with store.transaction(conn):
            if idempotency.record_or_skip(conn, activity_key, applied_at=ended_at):
                crm.emit_phone_call_activity(activity)

    # Queue-status update (always emitted per FR-029).
    new_status = _NEW_STATUS_MAP.get(disposition, queue_item.callable_status)
    status_payload = QueueStatusUpdatePayload(
        session_id=session.session_id,
        queue_item_id=queue_item.queue_item_id,
        previous_status=queue_item.callable_status,
        new_status=new_status,
        transition_reason=disposition.value,
        transition_at=ended_at,
    )
    status_key = idempotency.compute_key(
        session_id=session.session_id,
        mock_provider_call_id=mock_call_id,
        event_id=None,
        write_back_kind=WriteBackKind.QUEUE_STATUS_UPDATE,
    )
    with store.transaction(conn):
        if idempotency.record_or_skip(conn, status_key, applied_at=ended_at):
            crm.emit_queue_status_update(status_payload)

    # Task payload per FR-031.
    task: TaskPayload | None = None
    if disposition in _EMITS_CALLBACK_TASK:
        task = _build_callback_task(
            session=session, queue_item=queue_item, normalized=normalized, ended_at=ended_at
        )
    elif disposition in _EMITS_REVIEW_TASK:
        task = _build_review_task(
            session=session,
            queue_item=queue_item,
            persona_output=persona_output,
            ended_at=ended_at,
        )

    if task is not None:
        task_key = idempotency.compute_key(
            session_id=session.session_id,
            mock_provider_call_id=mock_call_id,
            event_id=None,
            write_back_kind=WriteBackKind.TASK_PAYLOAD,
        )
        with store.transaction(conn):
            if idempotency.record_or_skip(conn, task_key, applied_at=ended_at):
                crm.emit_task(task)

    writeback = crm.build_writeback(session.session_id)

    paths = write_session_artifacts(
        artifact_root=config.artifacts.dir,
        session_id=session.session_id,
        normalized_result=normalized,
        writeback=writeback,
        eligibility_decision=_to_exported_decision(decision),
        task=task,
        transcript_text=transcript_text,
        conflicting_events=conflicting_events or None,
    )

    # FINAL commit: flip the session to FINALIZED only now that every write-back row
    # and artifact has been persisted (N3) — a FINALIZED row is always complete.
    with store.transaction(conn):
        store.update_session(conn, session.session_id, state=SessionState.FINALIZED)

    return normalized, paths


def _build_normalized_result(
    *,
    session: Session,
    queue_item,
    mock_call_id: str,
    disposition: Disposition,
    persona_output: PersonaOutput | None,
    ended_at: str,
) -> NormalizedResult:
    if persona_output is not None:
        ex = persona_output.extraction
        summary = persona_output.summary
        return NormalizedResult(
            session_id=session.session_id,
            queue_item_id=queue_item.queue_item_id,
            mock_provider_call_id=mock_call_id,
            persona_version=persona_output.persona_version,
            final_disposition=disposition,
            summary=summary,
            transcript_pointer="transcript.txt",
            captured_email=ex.captured_email,
            captured_email_unverified=ex.captured_email_unverified,
            callback_requested=ex.callback_requested,
            preferred_callback_window=ex.preferred_callback_window,
            human_review_reason=persona_output.human_review_reason,
            blocked_reason=None,
            started_at=session.started_at,
            ended_at=ended_at,
        )
    return NormalizedResult(
        session_id=session.session_id,
        queue_item_id=queue_item.queue_item_id,
        mock_provider_call_id=mock_call_id,
        persona_version="alf-appointment-setter@0.1.0",
        final_disposition=disposition,
        summary=f"Disposition: {disposition.value}; no persona interaction.",
        transcript_pointer=None,
        callback_requested=False,
        blocked_reason=None,
        started_at=session.started_at,
        ended_at=ended_at,
    )


def _build_callback_task(
    *, session: Session, queue_item, normalized: NormalizedResult, ended_at: str
) -> TaskPayload:
    return TaskPayload(
        task_id=ids.new_task_id(),
        session_id=session.session_id,
        queue_item_id=queue_item.queue_item_id,
        task_kind="callback",
        subject=f"Callback for {queue_item.facility_name}",
        preferred_callback_window=normalized.preferred_callback_window,
        captured_email=normalized.captured_email,
        persona_version=normalized.persona_version or "alf-appointment-setter@0.1.0",
        created_at=ended_at,
    )


def _build_review_task(
    *,
    session: Session,
    queue_item,
    persona_output: PersonaOutput | None,
    ended_at: str,
) -> TaskPayload:
    reason = persona_output.human_review_reason if persona_output else None
    reason_label = reason.value if reason else "unknown"
    return TaskPayload(
        task_id=ids.new_task_id(),
        session_id=session.session_id,
        queue_item_id=queue_item.queue_item_id,
        task_kind="review",
        subject=f"Review {reason_label} for {queue_item.facility_name}",
        reason_code=reason,
        persona_version=(persona_output.persona_version if persona_output else "alf-appointment-setter@0.1.0"),
        created_at=ended_at,
    )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _to_exported_decision(decision) -> ExportedEligibilityDecision:
    return ExportedEligibilityDecision(
        decision_id=decision.decision_id,
        queue_item_id=decision.queue_item_id,
        session_id=decision.session_id,
        decided_at=decision.decided_at,
        outcome=decision.outcome,
        rules={
            "a": decision.rule_a_phone_pass,
            "b": decision.rule_b_timezone_pass,
            "c": decision.rule_c_call_window_pass,
            "d": decision.rule_d_dnc_pass,
            "e": decision.rule_e_max_attempts_pass,
            "f": decision.rule_f_callable_status_pass,
        },
        failing_rules=decision.failing_rules,
        default_tz_applied=decision.default_tz_applied,
        default_tz_substituted_for=decision.default_tz_substituted_for,
    )


def _format_transcript(turns: list[ConversationTurn]) -> str:
    """Render the conversation as one `[role] text` line per turn (research.md §Artifact)."""
    return "\n".join(f"[{t.role}] {t.text}" for t in turns)


_ = json  # keep import for future state-mutation helpers
_ = Path
