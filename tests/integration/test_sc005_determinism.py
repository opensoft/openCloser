"""T069 — SC-005 deterministic-JSON property test.

Running the same fixture twice in isolated temp directories MUST produce byte-identical
exported artifacts (excluding the session_id-keyed path, which is randomized by design).
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
_CONV = _REPO / "tests/fixtures/conversations/interested_callback_requested.json"
_TRANSPORT = _REPO / "tests/fixtures/transport_events"


def _load_conv() -> ConversationFixture:
    raw = json.loads(_CONV.read_text(encoding="utf-8"))
    return ConversationFixture(
        fixture_id=raw["fixture_id"],
        expected_disposition=raw["expected_disposition"],
        queue_item_ref=raw["queue_item_ref"],
        turns=[ConversationTurn(role=t["role"], text=t["text"]) for t in raw["turns"]],
        expected_extraction=raw["expected_extraction"],
    )


def _run(tmp_path: Path, transport_fixture_id: str = "connected") -> Path:
    state_db = tmp_path / "state.db"
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir(parents=True)
    config = SliceConfig(
        call_window=CallWindowConfig(start="09:00", end="20:00"),
        eligibility=EligibilityConfig(max_attempts=5, default_timezone="America/Los_Angeles"),
        artifacts=ArtifactsConfig(dir=str(artifact_dir)),
        persona=PersonaConfig(version="alf-appointment-setter@0.1.0"),
        state=StateConfig(db=str(state_db)),
    )
    conn = store.connect(state_db)
    store.init_schema(conn, now_utc_ms="2026-05-19T17:00:00.000Z")
    store.insert_queue_item(
        conn, QueueItem.model_validate_json(_QUEUE.read_text(encoding="utf-8"))
    )
    try:
        report = process_one_queue_item(
            "alf-prospect-001",
            conn=conn,
            config=config,
            eligibility=BuiltinEligibilityEvaluator(),
            transport=FixtureDrivenTransport(_TRANSPORT),
            persona=ALFAppointmentSetterPersona(),
            conversation_fixture=_load_conv(),
            transport_fixture_id=transport_fixture_id,
            clock=FrozenClock(datetime(2026, 5, 19, 19, 0, 0, tzinfo=UTC)),
        )
        return report.artifact_dir
    finally:
        conn.close()


def test_sc005_deterministic_artifact_keys_across_runs(tmp_path: Path) -> None:
    """Two independent runs of the same fixture produce JSON with identical sorted keys
    and byte-identical writeback structure (modulo session-id-keyed values)."""
    dir_a = _run(tmp_path / "a")
    dir_b = _run(tmp_path / "b")

    # Compare normalized bodies — strip the runtime-randomized session_id-prefixed values.
    def _normalize(path: Path) -> str:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        _strip_ids(data)
        return json.dumps(data, sort_keys=True, indent=2)

    for name in (
        "session-result.json",
        "writeback.json",
        "eligibility-decision.json",
        "task.json",
    ):
        a_text = _normalize(dir_a / name)
        b_text = _normalize(dir_b / name)
        assert a_text == b_text, f"{name} differs across runs"

    # transcript.txt carries no runtime ids — it is rendered verbatim from the fixture
    # turns, so it must be byte-identical across runs without any normalization.
    assert (dir_a / "transcript.txt").read_bytes() == (dir_b / "transcript.txt").read_bytes(), (
        "transcript.txt differs across runs"
    )


def test_sc005_conflicting_events_artifact_deterministic(tmp_path: Path) -> None:
    """The FR-020 audit artifact (conflicting-events.json) is also byte-deterministic
    across reruns of the same fixture, modulo the runtime-randomized audit/session ids."""
    dir_a = _run(tmp_path / "a", transport_fixture_id="conflicting_failed_after_completed")
    dir_b = _run(tmp_path / "b", transport_fixture_id="conflicting_failed_after_completed")

    def _normalize(path: Path) -> str:
        data = json.loads(path.read_text(encoding="utf-8"))
        _strip_ids(data)
        return json.dumps(data, sort_keys=True, indent=2)

    a_path = dir_a / "conflicting-events.json"
    b_path = dir_b / "conflicting-events.json"
    assert a_path.exists() and b_path.exists(), "conflicting-events.json was not exported"
    assert _normalize(a_path) == _normalize(b_path), "conflicting-events.json differs across runs"


def _strip_ids(obj) -> None:
    """Recursively zero out runtime-randomized id fields so cross-run structure can be compared."""
    if isinstance(obj, dict):
        for k in list(obj.keys()):
            if k in {"session_id", "decision_id", "task_id", "audit_id", "mock_provider_call_id"}:
                obj[k] = "__id__"
            else:
                _strip_ids(obj[k])
    elif isinstance(obj, list):
        for item in obj:
            _strip_ids(item)
