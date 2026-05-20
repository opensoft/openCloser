"""ALFAppointmentSetterPersona — the only Slice 1 persona.

Owns disclosure language, allowed claims (FR-009), extraction schema (FR-034),
escalation rules (FR-035), and disposition precedence (FR-036). Deterministic.
"""

from __future__ import annotations

from opencloser.models import Disposition, Extraction, HumanReviewReason
from opencloser.persona.base import (
    ConversationFixture,
    ConversationTurn,
    PersonaOutput,
    SessionContext,
)
from opencloser.persona.disposition_rules import decide_disposition
from opencloser.persona.escalation import derive_escalation_reason
from opencloser.persona.extraction import extract_from_turns

# Q2 — Slice 1 canonical disclosure first-utterance (exact string match).
CANONICAL_DISCLOSURE = (
    "Hi, this is an AI assistant calling on behalf of Medx, the senior-living placement "
    "service. Is this a good time to chat for two minutes?"
)

PERSONA_VERSION = "alf-appointment-setter@0.1.0"


class ALFAppointmentSetterPersona:
    """The Slice 1 ALF appointment-setter persona (scripted, deterministic)."""

    @property
    def version(self) -> str:
        return PERSONA_VERSION

    def run(
        self,
        session_context: SessionContext,
        conversation: ConversationFixture,
    ) -> PersonaOutput:
        # `session_context` is unused in Slice 1: the scripted-fixture persona is
        # fully deterministic and reads only `conversation`. The parameter is part
        # of the FR-033 / contracts/persona.md `run()` surface and is required so
        # the Slice 2 live persona can consume `clock`, `config`, and the
        # `queue_item` without a contract change. Deleted here to signal intent.
        del session_context
        turns = list(conversation.turns)
        disclosure_completed = _disclosure_completed(turns)

        if not disclosure_completed:
            return PersonaOutput(
                persona_version=self.version,
                final_disposition=Disposition.NEEDS_HUMAN_REVIEW,
                summary="Disclosure validation failed; first persona turn did not match canonical string.",
                extraction=_minimal_extraction(),
                human_review_reason=HumanReviewReason.OUTSIDE_ALLOWED_CLAIMS,
                disclosure_completed=False,
            )

        extraction = extract_from_turns(turns)
        # "Script terminated without signal" (FR-036 rule 10): the contact never
        # produced a substantive turn — every contact turn is a short pleasantry
        # (< 12 chars), or there were no contact turns at all. A single *long*
        # turn is NOT truncated: it carries enough signal to classify genuinely.
        contact_turns = [t for t in turns if t.role == "contact"]
        terminated = all(len(t.text.strip()) < 12 for t in contact_turns)

        escalation = derive_escalation_reason(
            extraction, turns, script_terminated_without_signal=terminated
        )
        disposition, review_reason = decide_disposition(
            extraction, escalation, script_terminated_without_signal=terminated
        )

        summary = _build_summary(disposition, extraction, review_reason)
        return PersonaOutput(
            persona_version=self.version,
            final_disposition=disposition,
            summary=summary,
            extraction=extraction,
            human_review_reason=review_reason,
            disclosure_completed=True,
        )


def _disclosure_completed(turns: list[ConversationTurn]) -> bool:
    """Byte-exact match of the first persona turn against the canonical disclosure.

    The contract (contracts/persona.md §Disclosure validator) mandates an exact
    string match with no paraphrases in Slice 1; surrounding whitespace is
    significant and is NOT stripped — a deviation, including a stray leading or
    trailing space, fails the validator.
    """
    persona_turns = [t for t in turns if t.role == "persona"]
    if not persona_turns:
        return False
    return persona_turns[0].text == CANONICAL_DISCLOSURE


def _minimal_extraction() -> Extraction:
    from opencloser.models import IntentClassification, RoleConfidence

    return Extraction(
        captured_email=None,
        captured_email_unverified=None,
        callback_requested=False,
        preferred_callback_window=None,
        role_confidence=RoleConfidence.UNCERTAIN,
        intent_classification=IntentClassification.UNCERTAIN,
        refusal_topics=[],
    )


def _build_summary(
    disposition: Disposition,
    extraction: Extraction,
    review_reason: HumanReviewReason | None,
) -> str:
    """One-sentence outcome per FR-014's `summary` (≤ 200 chars)."""
    parts: list[str] = [f"Disposition: {disposition.value}"]
    if extraction.callback_requested and extraction.preferred_callback_window:
        parts.append(f"callback {extraction.preferred_callback_window}")
    if extraction.captured_email:
        parts.append(f"email {extraction.captured_email}")
    elif extraction.captured_email_unverified:
        parts.append(f"email (unverified) {extraction.captured_email_unverified}")
    if review_reason:
        parts.append(f"review reason: {review_reason.value}")
    summary = "; ".join(parts) + "."
    return summary[:200]
