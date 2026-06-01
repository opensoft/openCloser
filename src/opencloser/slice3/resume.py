"""T057 — Slice 3 resume coordinator (Round 2 Q6 live-call abandonment).

When the operator re-invokes the CLI to resume a session that received the
SignalWire ``answered`` callback but never a normalized terminal event before the
orchestrator process died (or callback delivery failed persistently), the resume
invocation MUST (FR-026 / Round 2 Q6):

- immediately finalize the session as ``failed`` with reason
  ``live_call_abandonment`` — by the time a human re-invokes, the call has been
  silent past the abandonment timeout;
- NOT wait for further SignalWire callbacks and NOT reconnect to the provider's
  media stream;
- apply the Slice 2 resume / idempotency contract for any partial write-back.

This module owns the local finalization (session state + run report). The
Dataverse partial-write-back resume reuses the Slice 2 coordinator
(:func:`opencloser.slice2.resume.resume_session`) unchanged — Slice 3 adds no new
CRM write-back behavior here. The US7 multi-operator-identity and flag-on-resume
rules (Round 2 Q12 / Q13) layer on top in T087 / T088.
"""

from __future__ import annotations

import sqlite3

from opencloser.core.clock import Clock, SystemClock
from opencloser.models import Disposition, SessionState, Slice3RunMode
from opencloser.slice3.run_report import build_run_report, write_run_report
from opencloser.slice3.runner import (
    _ABANDONMENT_REASON,
    EXIT_LIVE_CALL_ABANDONMENT,
    RealCallRunReport,
)
from opencloser.state import store


class ResumeError(RuntimeError):
    """Raised when a resume invocation references an unknown session id."""


def resume_abandoned_session(
    session_id: str,
    *,
    conn: sqlite3.Connection,
    artifact_root: str,
    operator_id: str,
    run_mode: Slice3RunMode = Slice3RunMode.REAL_CALL,
    clock: Clock | None = None,
) -> RealCallRunReport:
    """Resume an answered-but-no-terminal session by finalizing it as abandonment.

    Loads the prior session, marks it ``finalized`` with disposition ``failed`` and
    failure reason ``live_call_abandonment`` (so the queue item does not remain
    ``in_progress`` indefinitely), writes the run report, and returns exit code 6.
    Raises :class:`ResumeError` if the session id is unknown. No SignalWire
    callbacks are awaited and no media stream is reconnected (Round 2 Q6).
    """
    clk = clock or SystemClock()
    session = store.get_session(conn, session_id)
    if session is None:
        raise ResumeError(f"session {session_id!r} not found; nothing to resume")

    ended_at = clk.now_utc_ms()
    if session.state is not SessionState.FINALIZED:
        with store.transaction(conn):
            store.update_session(
                conn,
                session_id,
                state=SessionState.FINALIZED,
                final_disposition=Disposition.FAILED,
                ended_at=ended_at,
            )

    report = build_run_report(
        session_id=session_id,
        run_mode=run_mode,
        operator_current=operator_id,
        real_provider_call_id=session.mock_provider_call_id,
        persona_version=session.persona_version or "",
        final_disposition=Disposition.FAILED,
        blocked_reason=_ABANDONMENT_REASON,
        started_at=session.started_at,
        ended_at=ended_at,
    )
    write_run_report(f"{artifact_root}/{session_id}", report)

    return RealCallRunReport(
        exit_status="live_call_abandonment",
        exit_code=EXIT_LIVE_CALL_ABANDONMENT,
        session_id=session_id,
        final_disposition=Disposition.FAILED,
        queue_item_id=session.queue_item_id,
        run_mode=run_mode,
        run_report=report,
        warnings=[f"resume finalized session {session_id} as {_ABANDONMENT_REASON} (Round 2 Q6)"],
    )


__all__ = ("ResumeError", "resume_abandoned_session")
