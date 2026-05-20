"""FR-034 persona extraction schema — deterministic rule-based extraction for Slice 1.

No randomness, no clock, no external IO. Inputs: the ordered conversation turns the
fixture provides. Outputs: a fully-populated `Extraction` per FR-034.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from opencloser.models import (
    Extraction,
    IntentClassification,
    RefusalTopic,
    RoleConfidence,
)
from opencloser.persona.base import ConversationTurn

# Q5 — DNC trigger phrases (case-insensitive substring match).
_DNC_PHRASES = (
    "don't call",
    "do not call",
    "stop calling",
    "take me off",
    "remove me",
    "do not contact",
    "unsubscribe",
    "opt out",
    "opt-out",
)

# Bare "this isn't " / "this is not " false-positived on unrelated negations
# ("this isn't urgent"). Narrowed to phrasings that genuinely signal the persona
# reached a non-facility / wrong number.
_WRONG_NUMBER_PHRASES = (
    "wrong number",
    "you have the wrong",
    "isn't a facility",
    "is not a facility",
    "not a facility",
    "this isn't the right number",
    "this is not the right number",
    "no facility here",
)

_NOT_INTERESTED_PHRASES = (
    "not interested",
    "no thank you",
    "no thanks",
    "we're not interested",
)

_CALL_BACK_LATER_PHRASES = (
    "call back later",
    "try later",
    "not a good time",
    "not the best time",
    "busy right now",
    "we'll get back",
)

_CALLBACK_REQUEST_PHRASES = (
    "call me back",
    "give me a callback",
    "callback",
    "call back",
    "schedule a call",
)

# C2 — affirmative-engagement phrases. A contact who engages positively (without
# requesting a callback or volunteering an email) is still classified INTERESTED;
# without these the classifier fell through to UNCERTAIN and FR-036 rules 6/7
# became unreachable behind a spurious `uncertain_intent` escalation.
_INTERESTED_PHRASES = (
    "interested",
    "tell me more",
    "sounds good",
    "sounds great",
    "sounds reasonable",
    "that works",
    "that sounds",
    "what's this about",
    "what is this about",
    "go ahead",
    "happy to",
    "love to hear",
)

# C2 — a contact volunteering an email address is itself an engaged (INTERESTED)
# signal, independent of the separate email-extraction pass.
_EMAIL_VOLUNTEER_PHRASES = (
    "send info to",
    "send it to",
    "send me",
    "email me",
    "email is",
    "email it to",
    "my email",
    "reach me at",
    "info pack",
)

# H6 — bare "i handle " false-positived on non-decision-maker duties ("I handle
# the laundry", "I handle calls"). Replaced with role-specific phrases that
# genuinely indicate placement-decision authority.
_DECISION_MAKER_PHRASES = (
    "i'm the owner",
    "i'm the manager",
    "i'm the administrator",
    "i'm the director",
    "i make those decisions",
    "i handle placement",
    "i handle admissions",
    "i handle the contracts",
    "i handle those decisions",
)

_NON_DECISION_MAKER_PHRASES = (
    "i just answer the phones",
    "i don't make those decisions",
    "you'd want to talk to",
    "not my call",
)

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

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

_OUTSIDE_ALLOWED_KEYWORDS = (
    "how much exactly",
    "exact cost",
    "what do you charge",
    "compared to brookdale",
    "compared to sunrise",
)

# Refusal-topic keyword sets (FR-034 / Q9 enum). MEDICAL_HISTORY and LEGAL_ADVICE
# reuse _PHI_KEYWORDS / _LEGAL_KEYWORDS; the three below complete the 7-value enum.
_CLINICAL_ADVICE_KEYWORDS = (
    "clinical advice",
    "medical advice",
    "should i take",
    "what medication",
    "what dose",
    "recommend a treatment",
)

_REGULATORY_KEYWORDS = (
    "regulation",
    "regulatory",
    "state law",
    "licensing requirement",
    "compliance rule",
)

_INSURANCE_DISPUTE_KEYWORDS = (
    "insurance",
    "medicare",
    "medicaid",
    "coverage dispute",
    "claim denied",
    "claim was denied",
)


def extract_from_turns(turns: Sequence[ConversationTurn]) -> Extraction:
    """Apply Slice 1 deterministic extraction rules to a scripted conversation."""
    contact_turns = [t for t in turns if t.role == "contact"]
    persona_turns = [t for t in turns if t.role == "persona"]

    intent = _classify_intent(contact_turns)
    role = _classify_role_confidence(contact_turns)
    callback_requested, callback_window = _extract_callback(contact_turns)
    captured_email, captured_email_unverified = _extract_email(persona_turns, contact_turns)
    refusal_topics = _extract_refusal_topics(contact_turns)

    return Extraction(
        captured_email=captured_email,
        captured_email_unverified=captured_email_unverified,
        callback_requested=callback_requested,
        preferred_callback_window=callback_window,
        role_confidence=role,
        intent_classification=intent,
        refusal_topics=refusal_topics,
    )


# ---------------------------------------------------------------------------
# Per-field helpers
# ---------------------------------------------------------------------------


def _classify_intent(contact_turns: Sequence[ConversationTurn]) -> IntentClassification:
    """First-match-wins order: DNC > wrong-number > not-interested > call-back-later > interested."""
    joined = _lower_join(contact_turns)
    if _any_in(joined, _DNC_PHRASES):
        return IntentClassification.DNC_STATED
    if _any_in(joined, _WRONG_NUMBER_PHRASES):
        return IntentClassification.WRONG_NUMBER
    if _any_in(joined, _NOT_INTERESTED_PHRASES):
        return IntentClassification.NOT_INTERESTED
    if _any_in(joined, _CALL_BACK_LATER_PHRASES) and not _any_in(joined, _CALLBACK_REQUEST_PHRASES):
        return IntentClassification.CALL_BACK_LATER
    if (
        _any_in(joined, _CALLBACK_REQUEST_PHRASES)
        or _any_in(joined, _INTERESTED_PHRASES)
        or _any_in(joined, _EMAIL_VOLUNTEER_PHRASES)
    ):
        return IntentClassification.INTERESTED
    return IntentClassification.UNCERTAIN


def _classify_role_confidence(contact_turns: Sequence[ConversationTurn]) -> RoleConfidence:
    joined = _lower_join(contact_turns)
    if _any_in(joined, _DECISION_MAKER_PHRASES):
        return RoleConfidence.CONFIDENT_DECISION_MAKER
    if _any_in(joined, _NON_DECISION_MAKER_PHRASES):
        return RoleConfidence.CONFIDENT_NON_DECISION_MAKER
    return RoleConfidence.UNCERTAIN


def _extract_callback(
    contact_turns: Sequence[ConversationTurn],
) -> tuple[bool, str | None]:
    """Return (callback_requested, preferred_callback_window).

    Window extraction is intentionally simple for Slice 1: if the contact's callback turn
    mentions a day/time phrase, capture the substring after the callback verb.
    """
    for turn in contact_turns:
        lowered = turn.text.lower()
        if not _any_in(lowered, _CALLBACK_REQUEST_PHRASES):
            continue
        # Try to capture a day-of-week or hour fragment after the callback verb.
        window = _capture_window_fragment(turn.text)
        return True, window
    return False, None


def _capture_window_fragment(text: str) -> str | None:
    """Best-effort: find the day/hour mention in the contact's turn."""
    day_re = re.compile(
        r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|next week|this afternoon|tonight|this evening)\b",
        re.IGNORECASE,
    )
    # An hour mention MUST carry an am/pm marker OR explicit :MM minutes — a bare
    # 1-2 digit number ("I'm 35", "for 2 people") is NOT a callback time.
    hour_re = re.compile(
        r"\b\d{1,2}(?::\d{2}\s*(?:am|pm)?|\s*(?:am|pm))\b",
        re.IGNORECASE,
    )
    day = day_re.search(text)
    hour = hour_re.search(text)
    if day and hour:
        return text[day.start() : hour.end()].strip()
    if day:
        return day.group(0)
    if hour:
        return hour.group(0)
    return None


def _extract_email(
    persona_turns: Sequence[ConversationTurn],
    contact_turns: Sequence[ConversationTurn],
) -> tuple[str | None, str | None]:
    """Return (captured_email_verified, captured_email_unverified).

    A captured email is VERIFIED iff the persona's next turn read it back AND a subsequent
    contact turn confirms ("yes", "that's right", "correct"). Otherwise it's unverified.
    The two are mutually exclusive (per FR-014).
    """
    candidate: str | None = None
    for turn in contact_turns:
        match = _EMAIL_RE.search(turn.text)
        if match:
            candidate = match.group(0)
            break
    if candidate is None:
        return None, None

    # Verification: the persona must have read it back AND the contact must confirm.
    confirmed = _was_email_read_back_and_confirmed(candidate, persona_turns, contact_turns)
    if confirmed:
        return candidate, None
    return None, candidate


def _was_email_read_back_and_confirmed(
    candidate: str,
    persona_turns: Sequence[ConversationTurn],
    contact_turns: Sequence[ConversationTurn],
) -> bool:
    read_back = any(candidate in turn.text for turn in persona_turns)
    if not read_back:
        return False
    confirmations = ("yes", "that's right", "that is right", "correct", "yep", "yeah")
    return any(_any_in(turn.text.lower(), confirmations) for turn in contact_turns[-3:])


def _extract_refusal_topics(contact_turns: Sequence[ConversationTurn]) -> list[RefusalTopic]:
    """Detect contact-raised topics the persona must refuse, drawn from the Q9 enum.

    Order of appended topics is deterministic (fixed sequence below); all seven
    `RefusalTopic` values are reachable.
    """
    joined = _lower_join(contact_turns)
    topics: list[RefusalTopic] = []
    if any(k in joined for k in _PHI_KEYWORDS):
        topics.append(RefusalTopic.MEDICAL_HISTORY)
    if any(k in joined for k in _CLINICAL_ADVICE_KEYWORDS):
        topics.append(RefusalTopic.CLINICAL_ADVICE)
    if any(k in joined for k in _LEGAL_KEYWORDS):
        topics.append(RefusalTopic.LEGAL_ADVICE)
    if any(k in joined for k in _REGULATORY_KEYWORDS):
        topics.append(RefusalTopic.REGULATORY_INTERPRETATION)
    if any(k in joined for k in _INSURANCE_DISPUTE_KEYWORDS):
        topics.append(RefusalTopic.INSURANCE_DISPUTE)
    if any(k in joined for k in ("compared to", "brookdale", "sunrise")):
        topics.append(RefusalTopic.COMPETITOR_COMPARISON)
    if any(k in joined for k in ("exact cost", "what do you charge", "how much exactly")):
        topics.append(RefusalTopic.PRICING_SPECIFIC)
    return topics


# ---------------------------------------------------------------------------
# Tiny helpers
# ---------------------------------------------------------------------------


def _lower_join(turns: Sequence[ConversationTurn]) -> str:
    return " ".join(t.text.lower() for t in turns)


def _any_in(haystack: str, needles: Sequence[str]) -> bool:
    return any(n in haystack for n in needles)
