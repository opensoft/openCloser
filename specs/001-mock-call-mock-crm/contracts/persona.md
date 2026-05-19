# Contract: ALF Appointment-Setter Persona

> **Note on syntax**: Python-flavored pseudo-code (`name: Type`) is used for readability across the team. Type-hint syntax is decorative; the authoritative contract is the prose description of operations, inputs, and outputs.

**Module boundary**: FR-033, principle #4
**Implementation**: `src/opencloser/persona/base.py` (interface) + `src/opencloser/persona/alf_appointment_setter.py` (Slice 1 persona)
**Owns** (per Constitution Alignment + FR-009): disclosure language, allowed claims, extraction schema, disposition rules, escalation rules, persona version
**MUST NOT contain**: orchestration logic, eligibility logic, transport-event-routing logic, vendor-specific payload assembly

---

## Public surface

```text
Persona (interface):
    @property
    version: str
        # FR-011. e.g. "alf-appointment-setter@0.1.0".

    run(session_context: SessionContext, conversation: ConversationFixture) -> PersonaOutput
        # Executes the scripted conversation against the persona's rules and returns
        # the canonical persona-produced outputs (extraction + disposition + summary).
```

---

## Input shape

```text
SessionContext:
    session_id: str
    queue_item: QueueItem
    mock_provider_call_id: str
    started_at: UtcMs
    config: SliceConfig
    clock: Clock

ConversationFixture:                       # see research.md §Persona fixture format
    fixture_id: str
    expected_disposition: Disposition       # used only by tests; persona MUST NOT read it
    turns: list[ConversationTurn]
    expected_extraction: dict               # used only by tests; persona MUST NOT read it

ConversationTurn:
    role: "persona" | "contact"
    text: str
```

The persona reads the `turns` array in order. For `role="persona"` turns it validates that the text satisfies the disclosure / allowed-claims rules. For `role="contact"` turns it applies its extraction schema and updates internal state.

---

## Output shape

```text
PersonaOutput:
    persona_version: str
    final_disposition: Disposition
    summary: str
    extraction: Extraction
    human_review_reason: HumanReviewReason | None
    disclosure_completed: bool              # used by an orchestrator-side audit assertion

Extraction (FR-034):
    callback_requested: bool
    preferred_callback_window: str | None
    captured_email: str | None              # verified emails ONLY
    captured_email_unverified: str | None   # mutually exclusive with captured_email
    role_confidence: "confident_decision_maker" | "confident_non_decision_maker" | "uncertain"
    intent_classification: "interested" | "not_interested" | "call_back_later" | "dnc_stated" | "wrong_number" | "uncertain"
    refusal_topics: list[str]
```

---

## Disposition rules (FR-036)

The persona MUST apply this precedence on the extracted signals at the end of the conversation. First match wins:

1. `intent_classification == "dnc_stated"` → `do_not_call`. Mid-call DNC handling per Edge Case "DNC stated mid-conversation" applies in addition (the orchestrator handles the `dnc_flag` / `callable_status` updates; the persona just emits the disposition).
2. `intent_classification == "wrong_number"` → `wrong_number`.
3. Any escalation reason in FR-035's enumeration triggers → `needs_human_review` with the matching `human_review_reason`.
4. `captured_email IS NOT NULL` (verified) AND `callback_requested == True` → `interested_callback_requested`. Both signals are recorded; the callback task payload carries the verified email per the Q5 Clarification.
5. `callback_requested == True` (no verified email, or unverified email) → `interested_callback_requested`. The unverified email (if any) MAY accompany the result but does NOT change the disposition.
6. `captured_email IS NOT NULL` (verified) AND `callback_requested == False` → `interested_email_captured`.
7. `captured_email_unverified IS NOT NULL` AND `callback_requested == False` → `needs_human_review` with `human_review_reason='captured_email_invalid_no_callback'`.
8. `intent_classification == "call_back_later"` → `call_back_later`.
9. `intent_classification == "not_interested"` → `not_interested`.
10. Script ended without a clear signal → `needs_human_review` with `human_review_reason='script_truncated'`.

The mapping MUST be deterministic — the persona MUST NOT use randomness, the current wall clock, or any external IO beyond the conversation fixture.

---

## Escalation reasons (FR-035)

`human_review_reason` MUST be drawn from this enumerated set when the disposition is `needs_human_review`. Each code has a pinned trigger condition (implemented in `persona/escalation.py`):

| Reason code | Trigger condition |
|---|---|
| `uncertain_role` | `role_confidence == 'uncertain'` |
| `uncertain_intent` | `intent_classification == 'uncertain'` AND `role_confidence != 'uncertain'` |
| `ambiguous_dnc` | Contact uses DNC-adjacent phrasing the persona can't disambiguate from "not interested right now" |
| `captured_email_invalid_no_callback` | FR-036 rule #7 (unverified email + no callback) |
| `phi_collection_risk` | Contact volunteers (or persona detects) any PHI data class enumerated in FR-010 |
| `legal_request` | Contact requests recording deletion, GDPR-style data access, or legal escalation |
| `non_clinical_topic_escalation` | Contact asks for clinical / legal / regulatory / insurance advice the persona can't answer |
| `outside_allowed_claims` | Contact asks for info outside FR-009's allowed-claim categories |
| `script_truncated` | Fixture ended without producing a disposition (FR-036 rule #10) |

Free-form reasons are forbidden in Slice 1. Future slices may extend the enumeration ONLY by appending new codes — existing codes MUST NOT be replaced or repurposed.

---

## Disclosure validator

The persona MUST verify that its FIRST turn (the first `role="persona"` entry in the fixture) is the exact canonical Slice 1 disclosure string:

```text
Hi, this is an AI assistant calling on behalf of Medx, the senior-living placement service. Is this a good time to chat for two minutes?
```

Match is exact-string (no paraphrases in Slice 1). If the first turn matches, `disclosure_completed=True`. If the first turn deviates from the canonical string, `disclosure_completed=False` AND the persona MUST emit disposition `needs_human_review` with `human_review_reason='outside_allowed_claims'` (the disclosure failure is treated as an out-of-bounds persona behavior). Future slices may introduce variants behind this same validator.

---

## Versioning

`persona_version` is a class attribute, format `alf-appointment-setter@MAJOR.MINOR.PATCH` (research.md §`persona_version` format). The Slice 1 version is `alf-appointment-setter@0.1.0`.

`MAJOR` bumps on FR-036 disposition-rule precedence changes; `MINOR` bumps on disclosure / allowed-claim language changes; `PATCH` bumps on bug fixes that preserve observable behavior.

---

## Dependencies allowed

- `opencloser.models` (Disposition, HumanReviewReason, Extraction, etc.)
- stdlib `re` for disclosure validation regex

## Dependencies forbidden

- `opencloser.state` (the orchestrator persists)
- `opencloser.transport`, `opencloser.eligibility`, `opencloser.crm`
- Any network IO, any live LLM, any randomness
