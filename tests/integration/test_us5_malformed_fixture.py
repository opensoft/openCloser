"""T036 — US5 integration tests: malformed transport fixtures are rejected before any
session row, attempt increment, or Dataverse queue change (SC-006).

Resolves GitHub issue #2. Covers each FR-020 rejection class:

- invalid JSON,
- missing ``events`` array,
- event missing ``type`` / ``event_id`` / ``timestamp``,
- missing fixture file.

These tests drive ``process_one_queue_item`` directly — the entry point that creates
sessions, mutates queue state, and increments attempts — and assert that on a malformed
fixture the orchestrator fails *before* writing any of those rows. This is the real
SC-006 anchor: if the orchestrator's pre-session ``transport.pre_validate_fixture``
gate ever regresses, these assertions catch it (a direct ``validate_fixture`` call
would not).

The pre-validation hook is deliberately side-effect-free (no call id allocated, no
real call dialed), preserving the long-standing "session row before call attempt"
ordering contract for any future real transport — ``place_call`` itself still runs
after session insert.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from opencloser.core.clock import FrozenClock
from opencloser.core.orchestrator import process_one_queue_item
from opencloser.crm.mock import MockWriteBackAdapter
from opencloser.eligibility.evaluator import BuiltinEligibilityEvaluator
from opencloser.models import (
    ArtifactsConfig,
    CallableStatus,
    CallWindowConfig,
    EligibilityConfig,
    PersonaConfig,
    QueueItem,
    SliceConfig,
    StateConfig,
)
from opencloser.persona.alf_appointment_setter import ALFAppointmentSetterPersona
from opencloser.state import store
from opencloser.transport.mock import FixtureDrivenTransport, MalformedFixtureError

pytestmark = pytest.mark.integration

_T = "2026-05-19T17:00:00.000Z"
_QI_ID = "alf-prospect-001"
_FIXTURE_ID = "us5_malformed"  # bare id; transport resolves to <tmp>/us5_malformed.json


def _seed_queue_item(conn: sqlite3.Connection) -> QueueItem:
    item = QueueItem(
        queue_item_id=_QI_ID,
        facility_name="Sunset Ridge ALF",
        phone_number="+15555550100",
        timezone="America/Los_Angeles",
        attempt_count=0,
        callable_status=CallableStatus.READY,
    )
    store.insert_queue_item(conn, item)
    return item


def _config(artifact_dir: Path, db_path: Path) -> SliceConfig:
    return SliceConfig(
        call_window=CallWindowConfig(start="00:00", end="23:59"),
        eligibility=EligibilityConfig(max_attempts=5, default_timezone="America/Los_Angeles"),
        artifacts=ArtifactsConfig(dir=str(artifact_dir)),
        persona=PersonaConfig(version="alf-appointment-setter@0.1.0"),
        state=StateConfig(db=str(db_path)),
    )


def _assert_no_state_mutation(conn: sqlite3.Connection, queue_item_id: str) -> None:
    """SC-006 anchor: a malformed fixture leaves the local state store untouched.

    - No session row,
    - No eligibility-decision row,
    - No mock-call event row,
    - No idempotency key (so neither the SESSION_STATE nor ATTEMPT_COUNT write fired),
    - The queue item's attempt_count is still 0 and its callable_status is still READY.
    """
    n_sessions = conn.execute("SELECT COUNT(*) AS n FROM sessions;").fetchone()["n"]
    assert n_sessions == 0, "no session row may be created for a malformed fixture"

    n_decisions = conn.execute("SELECT COUNT(*) AS n FROM eligibility_decisions;").fetchone()["n"]
    assert n_decisions == 0, "no eligibility-decision row may be persisted"

    n_events = conn.execute("SELECT COUNT(*) AS n FROM mock_call_events;").fetchone()["n"]
    assert n_events == 0, "no mock-call event row may be persisted"

    n_keys = conn.execute("SELECT COUNT(*) AS n FROM idempotency_keys;").fetchone()["n"]
    assert n_keys == 0, "no idempotency key may be recorded (no attempt, no state write)"

    item = store.get_queue_item(conn, queue_item_id)
    assert item is not None, "the queue item itself is preserved"
    assert item.attempt_count == 0, "attempt_count must remain 0"
    assert item.callable_status is CallableStatus.READY, "callable_status must remain READY"
    assert item.last_decision_at is None, (
        "last_decision_at must remain null — the decision was never persisted"
    )


# ---------------------------------------------------------------------------
# FR-020 rejection cases — each one parameterised with the malformed-fixture writer
# ---------------------------------------------------------------------------


def _write_invalid_json(tmp_path: Path) -> Path:
    path = tmp_path / f"{_FIXTURE_ID}.json"
    path.write_text("this is not { valid json", encoding="utf-8")
    return path


def _write_no_events_array(tmp_path: Path) -> Path:
    path = tmp_path / f"{_FIXTURE_ID}.json"
    path.write_text(json.dumps({"fixture_id": "no_events"}), encoding="utf-8")
    return path


def _write_event_missing_identity_field(tmp_path: Path) -> Path:
    path = tmp_path / f"{_FIXTURE_ID}.json"
    # The first event is well-formed; the second is missing 'timestamp' — the gate
    # must reject the fixture even though some events are well-formed.
    path.write_text(
        json.dumps(
            {
                "events": [
                    {"event_id": "e1", "type": "connected", "timestamp": _T},
                    {"event_id": "e2", "type": "completed"},
                ]
            }
        ),
        encoding="utf-8",
    )
    return path


def _missing_file(tmp_path: Path) -> Path:
    # Intentionally do not create the file; the transport resolver will look it up
    # and validate_fixture will raise MalformedFixtureError on the missing path.
    return tmp_path / f"{_FIXTURE_ID}.json"


_MALFORMED_CASES: list[tuple[str, Callable[[Path], Path]]] = [
    ("invalid_json", _write_invalid_json),
    ("no_events_array", _write_no_events_array),
    ("event_missing_identity_field", _write_event_missing_identity_field),
    ("missing_file", _missing_file),
]


# ---------------------------------------------------------------------------
# SC-006 end-to-end: process_one_queue_item rejects malformed fixture with no writes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("case", "make_fixture"),
    _MALFORMED_CASES,
    ids=lambda v: v if isinstance(v, str) else "",
)
def test_us5_orchestrator_rejects_malformed_fixture_with_no_state_mutations(
    tmp_state_db: sqlite3.Connection,
    tmp_artifact_dir: Path,
    tmp_path: Path,
    case: str,
    make_fixture: Callable[[Path], Path],
) -> None:
    """SC-006 / FR-019 / FR-020: ``process_one_queue_item`` MUST reject a malformed
    fixture before writing any session, eligibility decision, attempt, idempotency
    key, mock-call event, or queue-status change.

    The orchestrator's pre-session ``transport.pre_validate_fixture(...)`` hook is
    what makes this true — a regression that drops that call (or moves session
    creation back ahead of it) would surface here as a non-empty ``sessions`` /
    ``eligibility_decisions`` table after the expected ``MalformedFixtureError``.
    """
    del case  # parametrization label only
    _seed_queue_item(tmp_state_db)
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    make_fixture(fixtures_dir)

    with pytest.raises(MalformedFixtureError):
        process_one_queue_item(
            _QI_ID,
            conn=tmp_state_db,
            config=_config(tmp_artifact_dir, tmp_path / "slice1.db"),
            eligibility=BuiltinEligibilityEvaluator(),
            transport=FixtureDrivenTransport(fixtures_dir),
            persona=ALFAppointmentSetterPersona(),
            crm=MockWriteBackAdapter(tmp_state_db),
            conversation_fixture=None,
            transport_fixture_id=_FIXTURE_ID,
            clock=FrozenClock(datetime(2026, 5, 19, 19, 0, 0, tzinfo=UTC)),
        )

    _assert_no_state_mutation(tmp_state_db, _QI_ID)


def test_us5_malformed_fixture_error_is_value_error_for_cli_handler(
    tmp_state_db: sqlite3.Connection,
    tmp_artifact_dir: Path,
    tmp_path: Path,
) -> None:
    """The Slice 1 CLI catches ``(ValueError, OSError)`` for bad operator input. A
    malformed fixture must surface through that handler as ``error:`` + exit 2, not
    an uncaught traceback — so ``MalformedFixtureError`` must remain a ``ValueError``
    subclass even when raised through the full orchestrator stack."""
    _seed_queue_item(tmp_state_db)
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    _write_invalid_json(fixtures_dir)

    with pytest.raises(ValueError):  # MalformedFixtureError is a ValueError subclass
        process_one_queue_item(
            _QI_ID,
            conn=tmp_state_db,
            config=_config(tmp_artifact_dir, tmp_path / "slice1.db"),
            eligibility=BuiltinEligibilityEvaluator(),
            transport=FixtureDrivenTransport(fixtures_dir),
            persona=ALFAppointmentSetterPersona(),
            crm=MockWriteBackAdapter(tmp_state_db),
            conversation_fixture=None,
            transport_fixture_id=_FIXTURE_ID,
            clock=FrozenClock(datetime(2026, 5, 19, 19, 0, 0, tzinfo=UTC)),
        )
    _assert_no_state_mutation(tmp_state_db, _QI_ID)
