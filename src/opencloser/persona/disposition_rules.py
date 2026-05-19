"""FR-036 persona disposition rule precedence — deterministic, first-match-wins.

The 10-rule ordered list from FR-036 + Clarifications Round 2 mapped to a single
pure function `decide_disposition`. No randomness, no clock, no external IO.
"""

from __future__ import annotations

from opencloser.models import (
    Disposition,
    Extraction,
    HumanReviewReason,
    IntentClassification,
)


def decide_disposition(
    extraction: Extraction,
    escalation_reason: HumanReviewReason | None,
    *,
    script_terminated_without_signal: bool = False,
) -> tuple[Disposition, HumanReviewReason | None]:
    """Return (final_disposition, human_review_reason) per FR-036 precedence.

    `human_review_reason` is non-null only when disposition is `needs_human_review`.
    """
    intent = extraction.intent_classification

    # Rule 1: DNC stated.
    if intent is IntentClassification.DNC_STATED:
        return Disposition.DO_NOT_CALL, None

    # Rule 2: Wrong number.
    if intent is IntentClassification.WRONG_NUMBER:
        return Disposition.WRONG_NUMBER, None

    # Rule 3: Any escalation trigger.
    if escalation_reason is not None:
        return Disposition.NEEDS_HUMAN_REVIEW, escalation_reason

    # Rule 4: verified email AND callback → interested_callback_requested (Q5 carve-out).
    if extraction.captured_email is not None and extraction.callback_requested:
        return Disposition.INTERESTED_CALLBACK_REQUESTED, None

    # Rule 5: callback requested (with or without unverified email).
    if extraction.callback_requested:
        return Disposition.INTERESTED_CALLBACK_REQUESTED, None

    # Rule 6: verified email, no callback.
    if extraction.captured_email is not None:
        return Disposition.INTERESTED_EMAIL_CAPTURED, None

    # Rule 7: unverified email, no callback → needs_human_review.
    if extraction.captured_email_unverified is not None:
        return (
            Disposition.NEEDS_HUMAN_REVIEW,
            HumanReviewReason.CAPTURED_EMAIL_INVALID_NO_CALLBACK,
        )

    # Rule 8: explicit call_back_later.
    if intent is IntentClassification.CALL_BACK_LATER:
        return Disposition.CALL_BACK_LATER, None

    # Rule 9: explicit not_interested.
    if intent is IntentClassification.NOT_INTERESTED:
        return Disposition.NOT_INTERESTED, None

    # Rule 10: script ended without producing a disposition.
    if script_terminated_without_signal or intent is IntentClassification.UNCERTAIN:
        return Disposition.NEEDS_HUMAN_REVIEW, HumanReviewReason.SCRIPT_TRUNCATED

    # Defensive fallback (should not reach in well-formed fixtures).
    return Disposition.NEEDS_HUMAN_REVIEW, HumanReviewReason.SCRIPT_TRUNCATED
