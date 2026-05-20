"""US2 Story 2 — Block an ineligible record before any mock call (P2).

Independent Test (per spec §Story 2): for each disqualifying condition, the system
creates a `blocked` session, persists the eligibility decision with failing rule(s),
emits no Phone Call activity, does not increment attempt_count, and lets the operator
read the block reason from the exported eligibility-decision.json.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from opencloser.core.clock import FrozenClock
from opencloser.core.orchestrator import process_one_queue_item
from opencloser.eligibility.evaluator import BuiltinEligibilityEvaluator
from opencloser.models import (
    ArtifactsConfig,
    CallWindowConfig,
    Disposition,
    EligibilityConfig,
    PersonaConfig,
    QueueItem,
    SliceConfig,
    StateConfig,
)
from opencloser.persona.alf_appointment_setter import ALFAppointmentSetterPersona
from opencloser.state import store
from opencloser.transport.mock import FixtureDrivenTransport

pytestmark = pytest.mark.integration

_REPO = Path(__file__).resolve().parents[2]
_QUEUE_FIXTURES = _REPO / "tests/fixtures/queue_items"
_TRANSPORT_FIXTURES = _REPO / "tests/fixtures/transport_events"


def _config(artifact_dir: Path, db_path: Path) -> SliceConfig:
    return SliceConfig(
        call_window=CallWindowConfig(start="09:00", end="20:00"),
        eligibility=EligibilityConfig(max_attempts=5, default_timezone="America/Los_Angeles"),
        artifacts=ArtifactsConfig(dir=str(artifact_dir)),
        persona=PersonaConfig(version="alf-appointment-setter@0.1.0"),
        state=StateConfig(db=str(db_path)),
    )


def _load_queue_item(name: str) -> QueueItem:
    return QueueItem.model_validate_json((_QUEUE_FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


# Each case: (fixture name, clock instant, expected failing rule code).
# After-hours uses a clock at 04:00 Pacific (UTC 11:00 — well outside 09:00–20:00).
_CASES = [
    ("alf-prospect-dnc", datetime(2026, 5, 19, 19, 0, 0, tzinfo=UTC), "d"),
    ("alf-prospect-after-hours", datetime(2026, 5, 19, 11, 0, 0, tzinfo=UTC), "c"),
    ("alf-prospect-max-attempts", datetime(2026, 5, 19, 19, 0, 0, tzinfo=UTC), "e"),
    ("alf-prospect-missing-phone", datetime(2026, 5, 19, 19, 0, 0, tzinfo=UTC), "a"),
    ("alf-prospect-not-ready", datetime(2026, 5, 19, 19, 0, 0, tzinfo=UTC), "f"),
]


@pytest.mark.parametrize("fixture_name,clock_utc,expected_failing_rule", _CASES)
def test_us2_blocked_by_eligibility(
    tmp_state_db: sqlite3.Connection,
    tmp_artifact_dir: Path,
    tmp_path: Path,
    fixture_name: str,
    clock_utc: datetime,
    expected_failing_rule: str,
) -> None:
    qi = _load_queue_item(fixture_name)
    store.insert_queue_item(tmp_state_db, qi)

    report = process_one_queue_item(
        qi.queue_item_id,
        conn=tmp_state_db,
        config=_config(tmp_artifact_dir, tmp_path / "db"),
        eligibility=BuiltinEligibilityEvaluator(),
        transport=FixtureDrivenTransport(_TRANSPORT_FIXTURES),
        persona=ALFAppointmentSetterPersona(),
        conversation_fixture=None,
        transport_fixture_id=None,
        clock=FrozenClock(clock_utc),
    )

    # (a) session created in `blocked` terminal state with disposition `blocked`.
    assert report.final_disposition is Disposition.BLOCKED
    sess = store.get_session(tmp_state_db, report.session_id)
    assert sess is not None and sess.final_disposition is Disposition.BLOCKED
    assert sess.mock_provider_call_id is None

    # (b) eligibility decision persisted with every failing rule named.
    elig_path = report.artifact_dir / "eligibility-decision.json"
    assert elig_path.exists()
    parsed = json.loads(elig_path.read_text(encoding="utf-8"))
    assert parsed["outcome"] == "block"
    assert expected_failing_rule in parsed["failing_rules"]

    # (c) no Phone Call-like activity emitted (FR-017).
    n = tmp_state_db.execute("SELECT COUNT(*) AS n FROM phone_call_activities;").fetchone()["n"]
    assert n == 0

    # (d) attempt_count unchanged.
    qi_after = store.get_queue_item(tmp_state_db, qi.queue_item_id)
    assert qi_after is not None and qi_after.attempt_count == qi.attempt_count

    # (e) operator can read the block reason from artifacts.
    sr = json.loads((report.artifact_dir / "session-result.json").read_text(encoding="utf-8"))
    assert sr["final_disposition"] == "blocked"
    assert expected_failing_rule in sr.get("blocked_reason", [])

    # (f) FR-029 / FR-005(f): a queue-status update IS emitted for blocked sessions —
    # exactly once per processed queue-item ID (the eligibility block does not skip it).
    n = tmp_state_db.execute(
        "SELECT COUNT(*) AS n FROM queue_status_updates WHERE session_id = ?;",
        (report.session_id,),
    ).fetchone()["n"]
    assert n == 1

    # (g) FR-018 / FR-031: no callback or review task payload is emitted for `blocked`.
    n = tmp_state_db.execute("SELECT COUNT(*) AS n FROM task_payloads;").fetchone()["n"]
    assert n == 0


def test_us2_multi_rule_failure_lists_all_in_canonical_order(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path, tmp_path: Path
) -> None:
    """Records that fail multiple rules MUST have all of them in the decision (no short-circuit)."""
    bad_qi = QueueItem(
        queue_item_id="q_multi",
        facility_name="Bad ALF",
        phone_number=None,             # fails (a)
        timezone="America/Los_Angeles",
        attempt_count=5,                # fails (e)
        dnc_flag=True,                  # fails (d)
        callable_status="dnc",          # fails (f)
    )
    store.insert_queue_item(tmp_state_db, bad_qi)
    report = process_one_queue_item(
        "q_multi",
        conn=tmp_state_db,
        config=_config(tmp_artifact_dir, tmp_path / "db"),
        eligibility=BuiltinEligibilityEvaluator(),
        transport=FixtureDrivenTransport(_TRANSPORT_FIXTURES),
        persona=ALFAppointmentSetterPersona(),
        conversation_fixture=None,
        transport_fixture_id=None,
        clock=FrozenClock(datetime(2026, 5, 19, 19, 0, 0, tzinfo=UTC)),
    )
    assert report.final_disposition is Disposition.BLOCKED
    decision = json.loads((report.artifact_dir / "eligibility-decision.json").read_text())
    assert decision["failing_rules"] == ["a", "d", "e", "f"]
