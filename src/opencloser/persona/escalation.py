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

# N2 — genuinely DNC-adjacent phrasing the persona cannot disambiguate from a
# soft brush-off. Per spec.md FR-010 / Clarifications Round 2 Q5, "I'm busy",
# "we'll get back to you", and "not the best time" are explicitly NOT ambiguous
# DNC — they MUST route to `call_back_later` (handled in
# extraction._classify_intent via _CALL_BACK_LATER_PHRASES), so they are
# deliberately excluded from this set.
_AMBIGUOUS_DNC_KEYWORDS = ("don't really want to talk",)


def derive_escalation_reason(
    extraction: Extraction,
    turns: Sequence[ConversationTurn],
    *,
    script_terminated_without_signal: bool = False,
) -> HumanReviewReason | None:
    """Return the matching FR-035 reason code, or None if no escalation is warranted.

    Covers the FR-035 trigger-condition table (Clarifications Round 2 Q10). The two
    FR-035 codes whose trigger conditions are *defined as* FR-036 rules —
    `captured_email_invalid_no_callback` (rule 7) and `script_truncated` (rule 10) —
    are intentionally NOT produced here; `disposition_rules.decide_disposition`
    owns them so that rule 3 (escalation) does not pre-empt rules 6/7/10.

    H5 — escalation reason-code priority (first match wins). FR-035 does not pin a
    priority among reason codes, so this is the canonical Slice 1 order, mirrored in
    `contracts/persona.md` §Escalation reasons:

        1. legal_request
        2. phi_collection_risk
        3. non_clinical_topic_escalation
        4. outside_allowed_claims
        5. ambiguous_dnc
        6. uncertain_role
        7. uncertain_intent

    Rationale: SAFETY escalations (1-5) outrank UNCERTAINTY escalations (6-7) — a
    legal/PHI/clinical/out-of-bounds/DNC-adjacent signal is a hard compliance risk
    and must surface to a human even when the contact's role or intent also reads
    as uncertain. Within the safety group, the highest-liability signals (legal,
    PHI) are checked first. `uncertain_role` precedes `uncertain_intent` because a
    `role_confidence == 'uncertain'` reading also makes the intent reading
    untrustworthy, so the role gap is the more informative thing for a reviewer.
    Safety codes (1-5) are never suppressed; `uncertain_role` / `uncertain_intent`
    (6-7) are suppressed when a later FR-036 rule owns the conversation (see below).
    """
    joined_contact = " ".join(t.text.lower() for t in turns if t.role == "contact")

    # Always-on safety escalations — never suppressed by a competing FR-036 rule.
    if any(k in joined_contact for k in _LEGAL_KEYWORDS):
        return HumanReviewReason.LEGAL_REQUEST
    if any(k in joined_contact for k in _PHI_KEYWORDS):
        return HumanReviewReason.PHI_COLLECTION_RISK
    if any(k in joined_contact for k in _NON_CLINICAL_KEYWORDS):
        return HumanReviewReason.NON_CLINICAL_TOPIC_ESCALATION
    if any(k in joined_contact for k in _OUTSIDE_ALLOWED_KEYWORDS):
        return HumanReviewReason.OUTSIDE_ALLOWED_CLAIMS

    # `ambiguous_dnc` is a genuine DNC-adjacent safety signal — it outranks the
    # generic role/intent-uncertainty checks below and is never suppressed.
    if any(k in joined_contact for k in _AMBIGUOUS_DNC_KEYWORDS):
        return HumanReviewReason.AMBIGUOUS_DNC

    # C3/C4/C5 — `uncertain_role` / `uncertain_intent` are suppressed when a
    # *later* FR-036 rule already owns this conversation, so rule 3 does not
    # pre-empt it and break first-match-wins precedence:
    #   - a captured email (verified or unverified) → FR-036 rules 6 / 7
    #   - a signal-starved / truncated script       → FR-036 rule 10
    captured_email_present = (
        extraction.captured_email is not None or extraction.captured_email_unverified is not None
    )
    if captured_email_present or script_terminated_without_signal:
        return None

    if extraction.role_confidence is RoleConfidence.UNCERTAIN:
        return HumanReviewReason.UNCERTAIN_ROLE

    if (
        extraction.intent_classification is IntentClassification.UNCERTAIN
        and extraction.role_confidence is not RoleConfidence.UNCERTAIN
    ):
        return HumanReviewReason.UNCERTAIN_INTENT

    return None
