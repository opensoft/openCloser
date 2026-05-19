"""FR-035 persona escalation reason codes — pinned trigger conditions per Clarifications Round 2 Q10.

Pure function: given the extraction and the conversation turns, return the matching
`HumanReviewReason` (or None if no escalation is warranted).
"""

from __future__ import annotations

from collections.abc import Sequence

from opencloser.models import (
    Extraction,
    HumanReviewReason,
    IntentClassification,
    RoleConfidence,
)
from opencloser.persona.base import ConversationTurn

_PHI_KEYWORDS = (
    "medication",
    "diagnosis",
    "treatment plan",
    "fall risk",
    "cognitive",
    "dementia",
    "alzheimer",
    "hospice",
    "resident name",
    "room number",
)

_LEGAL_KEYWORDS = (
    "delete this recording",
    "gdpr",
    "right to be forgotten",
    "consult our attorney",
    "legal department",
)

_NON_CLINICAL_KEYWORDS = (
    "clinical advice",
    "medical advice",
    "should i take",
    "what medication",
    "what dose",
    "insurance coverage",
    "regulatory",
)

_OUTSIDE_ALLOWED_KEYWORDS = (
    "exact cost",
    "what do you charge",
    "how much exactly",
    "compared to brookdale",
    "compared to sunrise",
)

_AMBIGUOUS_DNC_KEYWORDS = (
    "i'm busy right now",
    "we'll get back",
    "don't really want to talk",
    "not the best time but",
)


def derive_escalation_reason(
    extraction: Extraction,
    turns: Sequence[ConversationTurn],
) -> HumanReviewReason | None:
    """Return the matching FR-035 reason code, or None if no escalation is warranted.

    Order matches the FR-035 trigger-condition table (Clarifications Round 2 Q10).
    """
    joined_contact = " ".join(t.text.lower() for t in turns if t.role == "contact")

    if any(k in joined_contact for k in _LEGAL_KEYWORDS):
        return HumanReviewReason.LEGAL_REQUEST
    if any(k in joined_contact for k in _PHI_KEYWORDS):
        return HumanReviewReason.PHI_COLLECTION_RISK
    if any(k in joined_contact for k in _NON_CLINICAL_KEYWORDS):
        return HumanReviewReason.NON_CLINICAL_TOPIC_ESCALATION
    if any(k in joined_contact for k in _OUTSIDE_ALLOWED_KEYWORDS):
        return HumanReviewReason.OUTSIDE_ALLOWED_CLAIMS

    if extraction.role_confidence is RoleConfidence.UNCERTAIN:
        return HumanReviewReason.UNCERTAIN_ROLE

    if (
        extraction.intent_classification is IntentClassification.UNCERTAIN
        and extraction.role_confidence is not RoleConfidence.UNCERTAIN
    ):
        return HumanReviewReason.UNCERTAIN_INTENT

    if any(k in joined_contact for k in _AMBIGUOUS_DNC_KEYWORDS):
        return HumanReviewReason.AMBIGUOUS_DNC

    return None
