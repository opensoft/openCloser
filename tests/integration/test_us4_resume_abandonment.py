"""T057 — US4: resume an answered-but-no-terminal session as abandonment (Q6).

Re-invoking to resume a session that received `answered` but no normalized
terminal event immediately finalizes it as `failed` / `live_call_abandonment`
(exit 6) — the queue item does not remain `in_progress`, no callbacks are
awaited, and no media stream is reconnected (FR-026 / Round 2 Q6).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from opencloser.models import CallableStatus, Disposition, QueueItem, Session, SessionState
from opencloser.slice3.resume import ResumeError, resume_abandoned_session
from opencloser.slice3.runner import EXIT_LIVE_CALL_ABANDONMENT
from opencloser.state import store

_QID = "22222222-2222-2222-2222-222222222222"

pytestmark = pytest.mark.integration

_STARTED_AT = "2026-05-22T19:00:00.000Z"


def _stage_in_flight_session(conn: sqlite3.Connection, session_id: str) -> None:
    """Insert a session that connected (answered) but never reached a terminal
    event — the in-flight state a process restart leaves behind."""
    store.insert_queue_item(
        conn,
        QueueItem(
            queue_item_id=_QID,
            facility_name="Sunage ALF",
            attempt_count=1,
            callable_status=CallableStatus.IN_PROGRESS,
        ),
    )
    store.insert_session(
        conn,
        Session(
            session_id=session_id,
            queue_item_id=_QID,
            persona_version=None,
            state=SessionState.IN_FLIGHT,
            final_disposition=None,
            mock_provider_call_id="CA-aband-001",
            started_at=_STARTED_AT,
            ended_at=None,
        ),
    )


def test_us4_resume_finalizes_in_flight_as_abandonment(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """Resuming an in-flight (answered-no-terminal) session finalizes abandonment."""
    session_id = "sess-aband-resume-001"
    _stage_in_flight_session(tmp_state_db, session_id)

    report = resume_abandoned_session(
        session_id,
        conn=tmp_state_db,
        artifact_root=str(tmp_artifact_dir),
        operator_id="operator-b",
    )

    assert report.exit_code == EXIT_LIVE_CALL_ABANDONMENT
    assert report.final_disposition is Disposition.FAILED
    assert report.run_report is not None
    assert report.run_report.blocked_reason == "live_call_abandonment"

    # The session no longer remains in_progress/in_flight.
    finalized = store.get_session(tmp_state_db, session_id)
    assert finalized is not None and finalized.state is SessionState.FINALIZED

    # The run report was written.
    assert (tmp_artifact_dir / session_id / "run_report.json").is_file()


def test_us4_resume_unknown_session_raises(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path
) -> None:
    """Resuming an unknown session id raises ResumeError."""
    with pytest.raises(ResumeError):
        resume_abandoned_session(
            "sess-does-not-exist",
            conn=tmp_state_db,
            artifact_root=str(tmp_artifact_dir),
            operator_id="operator-b",
        )
