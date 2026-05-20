"""T068 — SC-001 wall-time budget gate.

Asserts every Slice 1 fixture combination completes in < 60_000 ms on this machine.
The wall_time_ms field on the CLI output is the canonical instrumentation.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from opencloser.core.clock import FrozenClock
from opencloser.core.orchestrator import process_one_queue_item
from opencloser.crm.mock import MockWriteBackAdapter
from opencloser.eligibility.evaluator import BuiltinEligibilityEvaluator
from opencloser.models import (
    ArtifactsConfig,
    CallWindowConfig,
    EligibilityConfig,
    PersonaConfig,
    QueueItem,
    SliceConfig,
    StateConfig,
)
from opencloser.persona.alf_appointment_setter import ALFAppointmentSetterPersona
from opencloser.persona.base import ConversationFixture, ConversationTurn
from opencloser.state import store
from opencloser.transport.mock import FixtureDrivenTransport

pytestmark = pytest.mark.integration

_REPO = Path(__file__).resolve().parents[2]
_QUEUE = _REPO / "tests/fixtures/queue_items/alf-prospect-001.json"
_CONV_DIR = _REPO / "tests/fixtures/conversations"
_TRANSPORT = _REPO / "tests/fixtures/transport_events"

_CONV_FIXTURES = sorted(p.stem for p in _CONV_DIR.glob("*.json"))


def _config(artifact_dir: Path, db_path: Path) -> SliceConfig:
    return SliceConfig(
        call_window=CallWindowConfig(start="09:00", end="20:00"),
        eligibility=EligibilityConfig(max_attempts=5, default_timezone="America/Los_Angeles"),
        artifacts=ArtifactsConfig(dir=str(artifact_dir)),
        persona=PersonaConfig(version="alf-appointment-setter@0.1.0"),
        state=StateConfig(db=str(db_path)),
    )


def _load_conv(name: str) -> ConversationFixture:
    raw = json.loads((_CONV_DIR / f"{name}.json").read_text(encoding="utf-8"))
    return ConversationFixture(
        fixture_id=raw["fixture_id"],
        expected_disposition=raw["expected_disposition"],
        queue_item_ref=raw["queue_item_ref"],
        turns=[ConversationTurn(role=t["role"], text=t["text"]) for t in raw["turns"]],
        expected_extraction=raw["expected_extraction"],
    )


@pytest.mark.parametrize("conv_name", _CONV_FIXTURES)
def test_sc001_per_fixture_under_60s(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path, tmp_path: Path, conv_name: str
) -> None:
    """Connected-path budget: every scripted conversation fixture finishes under 60s."""
    store.insert_queue_item(
        tmp_state_db, QueueItem.model_validate_json(_QUEUE.read_text(encoding="utf-8"))
    )
    report = process_one_queue_item(
        "alf-prospect-001",
        conn=tmp_state_db,
        config=_config(tmp_artifact_dir, tmp_path / "db"),
        eligibility=BuiltinEligibilityEvaluator(),
        transport=FixtureDrivenTransport(_TRANSPORT),
        persona=ALFAppointmentSetterPersona(),
        crm=MockWriteBackAdapter(tmp_state_db),
        conversation_fixture=_load_conv(conv_name),
        transport_fixture_id="connected",
        clock=FrozenClock(datetime(2026, 5, 19, 19, 0, 0, tzinfo=UTC)),
    )
    assert report.wall_time_ms < 60_000


@pytest.mark.parametrize("transport_fixture", ["no_answer", "voicemail", "failed"])
def test_sc001_terminal_paths_under_60s(
    tmp_state_db: sqlite3.Connection,
    tmp_artifact_dir: Path,
    tmp_path: Path,
    transport_fixture: str,
) -> None:
    """Terminal-event budget: no_answer / voicemail / failed paths (no persona run)
    also complete within the SC-001 60s budget."""
    store.insert_queue_item(
        tmp_state_db, QueueItem.model_validate_json(_QUEUE.read_text(encoding="utf-8"))
    )
    report = process_one_queue_item(
        "alf-prospect-001",
        conn=tmp_state_db,
        config=_config(tmp_artifact_dir, tmp_path / "db"),
        eligibility=BuiltinEligibilityEvaluator(),
        transport=FixtureDrivenTransport(_TRANSPORT),
        persona=ALFAppointmentSetterPersona(),
        crm=MockWriteBackAdapter(tmp_state_db),
        conversation_fixture=None,
        transport_fixture_id=transport_fixture,
        clock=FrozenClock(datetime(2026, 5, 19, 19, 0, 0, tzinfo=UTC)),
    )
    assert report.wall_time_ms < 60_000


_QUEUE_FIXTURES = _REPO / "tests/fixtures/queue_items"

# Blocked-path cases: (queue fixture, clock instant that makes it block).
_BLOCKED_CASES = [
    ("alf-prospect-dnc", datetime(2026, 5, 19, 19, 0, 0, tzinfo=UTC)),
    ("alf-prospect-after-hours", datetime(2026, 5, 19, 11, 0, 0, tzinfo=UTC)),
    ("alf-prospect-max-attempts", datetime(2026, 5, 19, 19, 0, 0, tzinfo=UTC)),
    ("alf-prospect-missing-phone", datetime(2026, 5, 19, 19, 0, 0, tzinfo=UTC)),
    ("alf-prospect-not-ready", datetime(2026, 5, 19, 19, 0, 0, tzinfo=UTC)),
]


@pytest.mark.parametrize("fixture_name,clock_utc", _BLOCKED_CASES)
def test_sc001_blocked_paths_under_60s(
    tmp_state_db: sqlite3.Connection,
    tmp_artifact_dir: Path,
    tmp_path: Path,
    fixture_name: str,
    clock_utc: datetime,
) -> None:
    """Blocked-by-eligibility budget: every disqualifying-condition path also completes
    within the SC-001 60s budget."""
    qi = QueueItem.model_validate_json(
        (_QUEUE_FIXTURES / f"{fixture_name}.json").read_text(encoding="utf-8")
    )
    store.insert_queue_item(tmp_state_db, qi)
    report = process_one_queue_item(
        qi.queue_item_id,
        conn=tmp_state_db,
        config=_config(tmp_artifact_dir, tmp_path / "db"),
        eligibility=BuiltinEligibilityEvaluator(),
        transport=FixtureDrivenTransport(_TRANSPORT),
        persona=ALFAppointmentSetterPersona(),
        crm=MockWriteBackAdapter(tmp_state_db),
        conversation_fixture=None,
        transport_fixture_id=None,
        clock=FrozenClock(clock_utc),
    )
    assert report.eligibility_outcome == "block"
    assert report.wall_time_ms < 60_000
