"""Unit tests for persona disposition rules (FR-036), escalation (FR-035), and disclosure validator.

The persona's outputs MUST be deterministic — running on the same fixture twice
yields identical results.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from opencloser.core.clock import FrozenClock
from opencloser.models import (
    ArtifactsConfig,
    CallableStatus,
    CallWindowConfig,
    Disposition,
    EligibilityConfig,
    HumanReviewReason,
    IntentClassification,
    PersonaConfig,
    QueueItem,
    RoleConfidence,
    SliceConfig,
    StateConfig,
)
from opencloser.persona.alf_appointment_setter import (
    CANONICAL_DISCLOSURE,
    ALFAppointmentSetterPersona,
)
from opencloser.persona.base import ConversationFixture, ConversationTurn, SessionContext
from opencloser.persona.disposition_rules import decide_disposition
from opencloser.persona.escalation import derive_escalation_reason
from opencloser.persona.extraction import extract_from_turns

pytestmark = pytest.mark.module("persona")

_T = "2026-05-19T17:00:00.000Z"


def _session_context(qi: QueueItem | None = None) -> SessionContext:
    qi = qi or QueueItem(
        queue_item_id="q1",
        facility_name="Sunset Ridge",
        phone_number="+15555550100",
        timezone="America/Los_Angeles",
        attempt_count=0,
        callable_status=CallableStatus.READY,
    )
    config = SliceConfig(
        call_window=CallWindowConfig(start="09:00", end="20:00"),
        eligibility=EligibilityConfig(max_attempts=5, default_timezone="America/Los_Angeles"),
        artifacts=ArtifactsConfig(dir="./artifacts"),
        persona=PersonaConfig(version="alf-appointment-setter@0.1.0"),
        state=StateConfig(db="./state/slice1.db"),
    )
    return SessionContext(
        session_id="ses_1",
        queue_item=qi,
        mock_provider_call_id="call_x",
        started_at=_T,
        config=config,
        clock=FrozenClock(datetime(2026, 5, 19, 17, 0, 0, tzinfo=UTC)),
    )


def _fixture(
    name: str, turns: list[tuple[str, str]], *, expected: str = "x"
) -> ConversationFixture:
    return ConversationFixture(
        fixture_id=name,
        expected_disposition=expected,
        queue_item_ref="q1",
        turns=[ConversationTurn(role=r, text=t) for r, t in turns],
        expected_extraction={},
    )


def _disclosure() -> tuple[str, str]:
    return "persona", CANONICAL_DISCLOSURE


# ---------------------------------------------------------------------------
# Disclosure validator (Q2)
# ---------------------------------------------------------------------------


def test_disclosure_canonical_matches() -> None:
    persona = ALFAppointmentSetterPersona()
    fx = _fixture(
        "interested_callback",
        [
            _disclosure(),
            ("contact", "Sure. We need help placing a resident."),
            ("persona", "Great. When would be a good callback?"),
            ("contact", "Call me back Thursday at 2 PM."),
        ],
    )
    out = persona.run(_session_context(), fx)
    assert out.disclosure_completed is True


def test_disclosure_deviation_triggers_outside_allowed_claims() -> None:
    persona = ALFAppointmentSetterPersona()
    fx = _fixture(
        "bad_disclosure",
        [
            ("persona", "Hey there! Got a sec?"),  # NOT the canonical string
            ("contact", "Sure."),
        ],
    )
    out = persona.run(_session_context(), fx)
    assert out.disclosure_completed is False
    assert out.final_disposition is Disposition.NEEDS_HUMAN_REVIEW
    assert out.human_review_reason is HumanReviewReason.OUTSIDE_ALLOWED_CLAIMS


# ---------------------------------------------------------------------------
# FR-036 — one test per rule
# ---------------------------------------------------------------------------


def test_rule_1_dnc_stated() -> None:
    persona = ALFAppointmentSetterPersona()
    fx = _fixture(
        "dnc",
        [
            _disclosure(),
            ("contact", "Please don't call this number again."),
        ],
    )
    out = persona.run(_session_context(), fx)
    assert out.final_disposition is Disposition.DO_NOT_CALL


def test_rule_2_wrong_number() -> None:
    persona = ALFAppointmentSetterPersona()
    fx = _fixture(
        "wrong",
        [
            _disclosure(),
            ("contact", "You have the wrong number. We don't do that."),
        ],
    )
    out = persona.run(_session_context(), fx)
    assert out.final_disposition is Disposition.WRONG_NUMBER


def test_rule_3_escalation_phi_collection() -> None:
    persona = ALFAppointmentSetterPersona()
    fx = _fixture(
        "phi",
        [
            _disclosure(),
            ("contact", "Our resident has dementia and takes several medications daily."),
        ],
    )
    out = persona.run(_session_context(), fx)
    assert out.final_disposition is Disposition.NEEDS_HUMAN_REVIEW
    assert out.human_review_reason is HumanReviewReason.PHI_COLLECTION_RISK


def test_q8_decision_maker_with_uncertain_intent_escalates_uncertain_intent() -> None:
    """Clarifications Round 2 Q8: a confident decision-maker whose *intent* is
    uncertain → FR-036 rule 3 → needs_human_review with `uncertain_intent`
    (NOT `uncertain_role` — role_confidence and intent_classification are
    independent fields)."""
    persona = ALFAppointmentSetterPersona()
    fx = _fixture(
        "q8_role_known_intent_uncertain",
        [
            _disclosure(),
            (
                "contact",
                "I'm the owner here. I genuinely can't tell whether this would be a fit for us.",
            ),
        ],
    )
    out = persona.run(_session_context(), fx)
    assert out.extraction.role_confidence is RoleConfidence.CONFIDENT_DECISION_MAKER
    assert out.extraction.intent_classification is IntentClassification.UNCERTAIN
    assert out.final_disposition is Disposition.NEEDS_HUMAN_REVIEW
    assert out.human_review_reason is HumanReviewReason.UNCERTAIN_INTENT


def test_rule_4_verified_email_and_callback() -> None:
    persona = ALFAppointmentSetterPersona()
    fx = _fixture(
        "email_and_callback",
        [
            _disclosure(),
            ("contact", "I'm the owner of Sunset Ridge. Email is owner@sunset.example.com."),
            ("persona", "Got it — owner@sunset.example.com, correct?"),
            ("contact", "Yes that's right. Call me back Thursday at 2 PM."),
        ],
    )
    out = persona.run(_session_context(), fx)
    assert out.final_disposition is Disposition.INTERESTED_CALLBACK_REQUESTED
    assert out.extraction.captured_email == "owner@sunset.example.com"
    assert out.extraction.callback_requested is True


def test_rule_5_callback_no_email() -> None:
    persona = ALFAppointmentSetterPersona()
    fx = _fixture(
        "callback_only",
        [
            _disclosure(),
            ("contact", "I'm the manager. Call me back Thursday at 2 PM."),
        ],
    )
    out = persona.run(_session_context(), fx)
    assert out.final_disposition is Disposition.INTERESTED_CALLBACK_REQUESTED


def test_rule_6_verified_email_no_callback() -> None:
    persona = ALFAppointmentSetterPersona()
    fx = _fixture(
        "email_only",
        [
            _disclosure(),
            ("contact", "I'm the director. Send info to dir@sunset.example.com."),
            ("persona", "Got it — dir@sunset.example.com, correct?"),
            ("contact", "Yes that's right. Please send info."),
        ],
    )
    out = persona.run(_session_context(), fx)
    assert out.final_disposition is Disposition.INTERESTED_EMAIL_CAPTURED
    assert out.extraction.captured_email == "dir@sunset.example.com"


def test_rule_7_unverified_email_no_callback_yields_needs_human_review() -> None:
    persona = ALFAppointmentSetterPersona()
    fx = _fixture(
        "email_unverified",
        [
            _disclosure(),
            ("contact", "I'm the director. Send info to dir@sunset.example.com."),
            # No persona read-back / no contact confirmation → unverified.
        ],
    )
    out = persona.run(_session_context(), fx)
    assert out.final_disposition is Disposition.NEEDS_HUMAN_REVIEW
    assert out.human_review_reason is HumanReviewReason.CAPTURED_EMAIL_INVALID_NO_CALLBACK


def test_rule_8_call_back_later() -> None:
    persona = ALFAppointmentSetterPersona()
    fx = _fixture(
        "later",
        [
            _disclosure(),
            ("contact", "I'm the owner. Not a good time, try later this week please."),
        ],
    )
    out = persona.run(_session_context(), fx)
    assert out.final_disposition is Disposition.CALL_BACK_LATER


def test_rule_9_not_interested() -> None:
    persona = ALFAppointmentSetterPersona()
    fx = _fixture(
        "no",
        [
            _disclosure(),
            ("contact", "I'm the owner. Honestly, we're not interested in this service."),
        ],
    )
    out = persona.run(_session_context(), fx)
    assert out.final_disposition is Disposition.NOT_INTERESTED


def test_rule_10_script_truncated() -> None:
    persona = ALFAppointmentSetterPersona()
    fx = _fixture(
        "truncated",
        [
            _disclosure(),
            ("contact", "Sure."),  # < 12 chars, no clear signal
        ],
    )
    out = persona.run(_session_context(), fx)
    assert out.final_disposition is Disposition.NEEDS_HUMAN_REVIEW
    assert out.human_review_reason is HumanReviewReason.SCRIPT_TRUNCATED


# ---------------------------------------------------------------------------
# Determinism (SC-005 + FR-036 mandate)
# ---------------------------------------------------------------------------


def test_persona_is_deterministic() -> None:
    persona = ALFAppointmentSetterPersona()
    fx = _fixture(
        "deterministic",
        [
            _disclosure(),
            ("contact", "I'm the owner. Call me back Thursday at 2 PM."),
        ],
    )
    out_a = persona.run(_session_context(), fx)
    out_b = persona.run(_session_context(), fx)
    assert out_a == out_b


# ---------------------------------------------------------------------------
# Persona version is the FR-011 canonical string
# ---------------------------------------------------------------------------


def test_persona_version_is_canonical_semver() -> None:
    persona = ALFAppointmentSetterPersona()
    assert persona.version == "alf-appointment-setter@0.1.0"


# ---------------------------------------------------------------------------
# Direct unit coverage of helpers
# ---------------------------------------------------------------------------


def test_extract_email_unverified_when_no_readback() -> None:
    turns = [
        ConversationTurn(role="persona", text=CANONICAL_DISCLOSURE),
        ConversationTurn(role="contact", text="My email is alice@example.com"),
    ]
    extraction = extract_from_turns(turns)
    assert extraction.captured_email is None
    assert extraction.captured_email_unverified == "alice@example.com"


def test_decide_disposition_rule_priority() -> None:
    """DNC (rule 1) beats wrong-number (rule 2) if both somehow appear."""
    from opencloser.models import IntentClassification, RoleConfidence

    extraction = type(extract_from_turns([ConversationTurn("contact", "")]))(
        captured_email=None,
        captured_email_unverified=None,
        callback_requested=False,
        preferred_callback_window=None,
        role_confidence=RoleConfidence.CONFIDENT_DECISION_MAKER,
        intent_classification=IntentClassification.DNC_STATED,
        refusal_topics=[],
    )
    disp, reason = decide_disposition(extraction, None)
    assert disp is Disposition.DO_NOT_CALL
    assert reason is None


def test_escalation_legal_request_beats_uncertain_role() -> None:
    """Legal request signal trumps role-uncertainty in the escalation ordering."""
    from opencloser.models import Extraction, IntentClassification, RoleConfidence

    extraction = Extraction(
        captured_email=None,
        captured_email_unverified=None,
        callback_requested=False,
        preferred_callback_window=None,
        role_confidence=RoleConfidence.UNCERTAIN,
        intent_classification=IntentClassification.INTERESTED,
        refusal_topics=[],
    )
    turns = [ConversationTurn(role="contact", text="Please delete this recording.")]
    reason = derive_escalation_reason(extraction, turns)
    assert reason is HumanReviewReason.LEGAL_REQUEST
