"""US6 Story 6 — Transcript redaction layer (P3, SC-009).

Independent Test (per spec §Story 6):

  Run a scripted conversation whose transcript contains a redaction-policy match;
  confirm the written artifact stores ``[REDACTED]``. Re-run with summary-only
  retention; confirm no transcript file is written while the session-result
  summary remains.

Also covers FR-029 (no-op policy preserves the Slice 1 artifact contract) and
the readiness-failure surface for a malformed redaction policy.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from opencloser.artifacts.writer import write_session_artifacts
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
    RedactionPolicyConfig,
    SliceConfig,
    StateConfig,
)
from opencloser.persona.alf_appointment_setter import ALFAppointmentSetterPersona
from opencloser.persona.base import ConversationFixture, ConversationTurn
from opencloser.redaction.layer import DEFAULT_REPLACEMENT, RedactionLayer
from opencloser.state import store
from opencloser.transport.mock import FixtureDrivenTransport
from tests.fixtures.artifact_inputs import make_artifact_inputs

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_QUEUE_ITEM_FIXTURE = _REPO_ROOT / "tests/fixtures/queue_items/alf-prospect-001.json"
_TRANSPORT_FIXTURES = _REPO_ROOT / "tests/fixtures/transport_events"

_SUMMARY = "Interested; callback requested for Thursday 14:00."
_TRANSCRIPT_WITH_PII = (
    "[persona] Could I confirm the best callback number?\n"
    "[contact] Yes, it's 555-123-4567 and email alice@example.com.\n"
    "[persona] Thank you — I'll have someone follow up.\n"
)


def _inputs(session_id: str) -> dict[str, object]:
    return make_artifact_inputs(session_id, transcript_text=_TRANSCRIPT_WITH_PII, summary=_SUMMARY)


def test_us6_redacted_token_written_to_transcript(tmp_artifact_dir: Path) -> None:
    """Spec §Story 6 acceptance: transcript file contains ``[REDACTED]`` and not the
    original PII when the default regex policy is in effect."""
    session_id = "ses_us6"
    layer = RedactionLayer.from_config(RedactionPolicyConfig())  # regex / full
    paths = write_session_artifacts(
        artifact_root=tmp_artifact_dir,
        session_id=session_id,
        redaction_layer=layer,
        **_inputs(session_id),
    )
    assert paths.transcript is not None and paths.transcript.exists()
    content = paths.transcript.read_text(encoding="utf-8")
    assert "555-123-4567" not in content
    assert "alice@example.com" not in content
    assert DEFAULT_REPLACEMENT in content
    sr = json.loads(paths.session_result.read_text(encoding="utf-8"))
    assert sr["summary"] == _SUMMARY
    assert sr["transcript_pointer"] == "transcript.txt"


def test_us6_summary_only_retention_writes_no_transcript(tmp_artifact_dir: Path) -> None:
    """Spec §Story 6 acceptance: summary-only retention writes NO transcript file;
    the session-result summary remains and the transcript pointer is null so no
    artifact reader can be led to a file that does not exist (FR-030)."""
    session_id = "ses_us6_sum"
    layer = RedactionLayer.from_config(
        RedactionPolicyConfig(policy="regex", retention="summary-only")
    )
    paths = write_session_artifacts(
        artifact_root=tmp_artifact_dir,
        session_id=session_id,
        redaction_layer=layer,
        **_inputs(session_id),
    )
    assert paths.transcript is None
    assert not (tmp_artifact_dir / session_id / "transcript.txt").exists()
    sr = json.loads(paths.session_result.read_text(encoding="utf-8"))
    assert sr["summary"] == _SUMMARY
    assert sr["transcript_pointer"] is None


def test_us6_noop_policy_preserves_slice1_contract(tmp_artifact_dir: Path) -> None:
    """FR-029: explicit no-op policy preserves the unredacted transcript contract."""
    session_id = "ses_us6_noop"
    layer = RedactionLayer.from_config(RedactionPolicyConfig(policy="noop"))
    paths = write_session_artifacts(
        artifact_root=tmp_artifact_dir,
        session_id=session_id,
        redaction_layer=layer,
        **_inputs(session_id),
    )
    assert paths.transcript is not None and paths.transcript.exists()
    content = paths.transcript.read_text(encoding="utf-8")
    assert "555-123-4567" in content
    assert "alice@example.com" in content
    assert DEFAULT_REPLACEMENT not in content


def test_us6_summary_only_removes_stale_transcript(tmp_artifact_dir: Path) -> None:
    """FR-030 + FR-019: re-emitting a session under summary-only retention must NOT
    leave a transcript file from a prior full-retention run on disk."""
    session_id = "ses_us6_rerun"
    full_layer = RedactionLayer.from_config(RedactionPolicyConfig())  # regex / full
    write_session_artifacts(
        artifact_root=tmp_artifact_dir,
        session_id=session_id,
        redaction_layer=full_layer,
        **_inputs(session_id),
    )
    stale = tmp_artifact_dir / session_id / "transcript.txt"
    assert stale.exists()

    summary_only_layer = RedactionLayer.from_config(
        RedactionPolicyConfig(policy="regex", retention="summary-only")
    )
    paths = write_session_artifacts(
        artifact_root=tmp_artifact_dir,
        session_id=session_id,
        redaction_layer=summary_only_layer,
        **_inputs(session_id),
    )
    assert paths.transcript is None
    assert not stale.exists(), "Stale transcript must be removed under summary-only retention"
    sr = json.loads(paths.session_result.read_text(encoding="utf-8"))
    assert sr["transcript_pointer"] is None


def test_us6_no_transcript_text_nulls_pointer_and_removes_stale(
    tmp_artifact_dir: Path,
) -> None:
    """When the caller supplies no transcript text, ``transcript_pointer`` must be
    null in session-result.json AND any transcript file from an earlier run must
    be removed so the exported pointer stays consistent with what is on disk."""
    session_id = "ses_us6_none"

    # Prime the session dir with a stale transcript file (as if a prior run wrote one).
    write_session_artifacts(
        artifact_root=tmp_artifact_dir,
        session_id=session_id,
        **_inputs(session_id),
    )
    stale = tmp_artifact_dir / session_id / "transcript.txt"
    assert stale.exists()

    # Now re-emit with no transcript text — the writer must clean up.
    paths = write_session_artifacts(
        artifact_root=tmp_artifact_dir,
        session_id=session_id,
        # No redaction_layer here — exercising the cached no-op fallback layer
        # (Copilot PR #3 LOW: the writer's silent fallback is now noop, not
        # default-on; transcript_text=None means the unlink path is what's
        # under test here, not the redaction behavior).
        **make_artifact_inputs(session_id, transcript_text=None, summary=_SUMMARY),
    )
    assert paths.transcript is None
    assert not stale.exists(), "Stale transcript must be removed when no transcript_text supplied"
    sr = json.loads(paths.session_result.read_text(encoding="utf-8"))
    assert sr["transcript_pointer"] is None
    assert sr["summary"] == _SUMMARY


def test_us6_malformed_policy_fails_readiness() -> None:
    """SC-009 / FR-028 readiness gate: a malformed regex in ``[redaction] patterns``
    fails layer construction — the orchestrator surfaces this as a readiness failure
    before any session is run."""
    bad_cfg = RedactionPolicyConfig(policy="regex", patterns=[r"(?P<bad"])
    with pytest.raises(ValueError, match="Invalid redaction regex"):
        RedactionLayer.from_config(bad_cfg)


# ---------------------------------------------------------------------------
# Orchestrator wiring — confirms the RedactionLayer passed into
# ``process_one_queue_item`` reaches the artifact writer end-to-end.
# ---------------------------------------------------------------------------


def _slice1_config(artifact_dir: Path, db_path: Path) -> SliceConfig:
    return SliceConfig(
        call_window=CallWindowConfig(start="09:00", end="20:00"),
        eligibility=EligibilityConfig(max_attempts=5, default_timezone="America/Los_Angeles"),
        artifacts=ArtifactsConfig(dir=str(artifact_dir)),
        persona=PersonaConfig(version="alf-appointment-setter@0.1.0"),
        state=StateConfig(db=str(db_path)),
    )


def _conversation_with_pii() -> ConversationFixture:
    return ConversationFixture(
        fixture_id="us6_pii_conversation",
        expected_disposition="interested_callback_requested",
        queue_item_ref="alf-prospect-001",
        turns=[
            ConversationTurn(
                role="persona",
                text="Hi, this is an AI assistant from Medx. Is this a good time?",
            ),
            ConversationTurn(
                role="contact",
                text=(
                    "Sure, I'm the owner. You can reach me at 555-123-4567 "
                    "or owner@sunsetridge.example. Call me back Thursday at 2 PM please."
                ),
            ),
            ConversationTurn(
                role="persona",
                text="Great — Thursday at 2 PM Pacific. Thanks for your time!",
            ),
        ],
        expected_extraction={
            "callback_requested": True,
            "preferred_callback_window": "Thursday at 2 PM",
            "role_confidence": "confident_decision_maker",
            "intent_classification": "interested",
        },
    )


def test_us6_orchestrator_passes_redaction_layer_to_writer(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path, tmp_path: Path
) -> None:
    """End-to-end wiring proof: a ``RedactionLayer`` built from Slice 2
    ``[redaction]`` config and passed into ``process_one_queue_item`` reaches the
    artifact writer, so operator-configured patterns / policy / retention actually
    take effect in the production call path (addresses the layer-not-wired gap)."""
    store.insert_queue_item(
        tmp_state_db,
        QueueItem.model_validate_json(_QUEUE_ITEM_FIXTURE.read_text(encoding="utf-8")),
    )
    layer = RedactionLayer.from_config(RedactionPolicyConfig())  # default-on regex

    report = process_one_queue_item(
        "alf-prospect-001",
        conn=tmp_state_db,
        config=_slice1_config(tmp_artifact_dir, tmp_path / "slice1.db"),
        eligibility=BuiltinEligibilityEvaluator(),
        transport=FixtureDrivenTransport(_TRANSPORT_FIXTURES),
        persona=ALFAppointmentSetterPersona(),
        crm=MockWriteBackAdapter(tmp_state_db),
        conversation_fixture=_conversation_with_pii(),
        transport_fixture_id="connected",
        clock=FrozenClock(datetime(2026, 5, 19, 19, 0, 0, tzinfo=UTC)),
        redaction_layer=layer,
    )

    transcript_path = report.artifact_dir / "transcript.txt"
    assert transcript_path.exists()
    content = transcript_path.read_text(encoding="utf-8")
    assert "555-123-4567" not in content
    assert "owner@sunsetridge.example" not in content
    assert DEFAULT_REPLACEMENT in content


def test_us6_orchestrator_summary_only_retention_omits_transcript(
    tmp_state_db: sqlite3.Connection, tmp_artifact_dir: Path, tmp_path: Path
) -> None:
    """When the orchestrator receives a summary-only layer, the writer emits no
    transcript file and session-result.json carries a null transcript_pointer."""
    store.insert_queue_item(
        tmp_state_db,
        QueueItem.model_validate_json(_QUEUE_ITEM_FIXTURE.read_text(encoding="utf-8")),
    )
    layer = RedactionLayer.from_config(
        RedactionPolicyConfig(policy="regex", retention="summary-only")
    )

    report = process_one_queue_item(
        "alf-prospect-001",
        conn=tmp_state_db,
        config=_slice1_config(tmp_artifact_dir, tmp_path / "slice1.db"),
        eligibility=BuiltinEligibilityEvaluator(),
        transport=FixtureDrivenTransport(_TRANSPORT_FIXTURES),
        persona=ALFAppointmentSetterPersona(),
        crm=MockWriteBackAdapter(tmp_state_db),
        conversation_fixture=_conversation_with_pii(),
        transport_fixture_id="connected",
        clock=FrozenClock(datetime(2026, 5, 19, 19, 0, 0, tzinfo=UTC)),
        redaction_layer=layer,
    )

    assert not (report.artifact_dir / "transcript.txt").exists()
    sr = json.loads((report.artifact_dir / "session-result.json").read_text(encoding="utf-8"))
    assert sr["transcript_pointer"] is None

    # DB consistency: the persisted normalized_result row must also have null
    # transcript_pointer so the DB does not advertise a file the writer skipped.
    row = tmp_state_db.execute(
        "SELECT transcript_pointer FROM normalized_results WHERE session_id = ?;",
        (report.session_id,),
    ).fetchone()
    assert row is not None and row["transcript_pointer"] is None
