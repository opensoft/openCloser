# Persona Module Requirements Quality Checklist: Slice 1 — Mock Call, Mock CRM

**Purpose**: Validate the quality, clarity, and completeness of the ALF appointment-setter persona's requirements — disclosure, allowed claims, extraction schema, disposition rules, escalation rules, versioning, and boundary contract. Unit tests for the *requirements*, not for the implementation.

**Created**: 2026-05-19
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 - Are the persona's five responsibilities (disclosure language, allowed claims, extraction schema, disposition rules, escalation rules) enumerated as distinct, individually testable deliverables? [Completeness, Spec §Constitution Alignment + §FR-009]
- [x] CHK002 - Is the persona's extraction schema's exact field set enumerated (captured_email, callback_requested flag, preferred_callback_window, role_confidence, intent_classification, any others)? [Gap, Spec §FR-009 + §FR-014] → **RESOLVED-BY-FR-034**
- [x] CHK003 - Are the persona's disposition rules — which extracted signals map to which disposition — enumerated for each of FR-013's ten dispositions? [Gap, Spec §FR-009 + §FR-013] → **RESOLVED-BY-FR-036**
- [x] CHK004 - Are the persona's escalation rules (which conversation states trigger `needs_human_review` with which reason codes) enumerated as a finite set? [Gap, Spec §FR-010 + §FR-014] → **RESOLVED-BY-FR-035**
- [x] CHK005 - Are the persona's versioning rules specified (version-string format, when bumped, where stored, how propagated to session/write-back)? [Gap, Spec §FR-011]
- [x] CHK006 - Is the persona's allowed-claims set enumerated with category-level granularity (services offered, pricing, scheduling, geographic coverage, etc.)? [Gap, Spec §FR-009]
- [x] CHK007 - Is the persona's mandatory disclosure language specified with exact wording or a paraphrase template? [Completeness, Spec §FR-010]

## Requirement Clarity

- [x] CHK008 - Is "scripted / fixture-driven conversation" defined precisely (turn-based JSON transcript, state-machine descriptor, branching script DSL, free-form text)? [Ambiguity, Spec §FR-009 + §Assumptions]
- [x] CHK009 - Is the boundary between "persona owns" and "Interaction Core owns" specified clearly enough to gate code review (e.g., disposition rules in persona, attempt-count increment in core)? [Clarity, Spec §Constitution Alignment]
- [x] CHK010 - Is "verified email" defined precisely per the Slice 1 clarification (syntactic validity AND explicit read-back / confirmation in the scripted conversation)? [Clarity, Spec §Assumptions]
- [x] CHK011 - Is "uncertainty" for human-review escalation defined operationally (confidence-threshold-based, rule-based, both)? [Ambiguity, Spec §FR-010]
- [x] CHK012 - Is "owns disclosure language" defined as ownership-of-string vs. ownership-of-policy (i.e., can the orchestrator override the disclosure wording at runtime)? [Clarity, Spec §Constitution Alignment + §FR-009]

## Requirement Consistency

- [x] CHK013 - Are the persona's disclosure requirements (FR-010) consistent across every connected-conversation acceptance scenario in Story 1 (does each scenario imply disclosure occurred)? [Consistency, Spec §FR-010 + §Story 1]
- [x] CHK014 - Is the persona's "MUST mark uncertainty for human review with a stated reason" (FR-010) consistent with the `human_review_reason` field in FR-014 (same field, same content)? [Consistency, Spec §FR-010 + §FR-014]
- [x] CHK015 - Is the persona's authority over disposition rules (FR-009) consistent with FR-018's hard constraint that certain dispositions never emit task payloads — i.e., is the persona's choice of disposition constrained by FR-018 or independent? [Consistency, Spec §FR-009 + §FR-018]
- [x] CHK016 - Is the persona's version (FR-011) consistently referenced across the Session entity, the Normalized Result fields, the Task Payload, and the Phone Call-like activity payload (or is it absent from some of these)? [Consistency, Spec §FR-011 + §FR-014 + §FR-015]
- [x] CHK017 - Are the persona's responsibilities (disclosure language, allowed claims, extraction schema, disposition rules, escalation rules) consistently named between the Constitution Alignment section and FR-009 (same five items, same wording)? [Consistency, Spec §Constitution Alignment + §FR-009]

## Acceptance Criteria Quality

- [x] CHK018 - Is the `persona_version` (FR-011) recorded in a format that allows two distinct test runs against the same persona version to be compared byte-for-byte deterministically? [Measurability, Spec §FR-011]
- [x] CHK019 - Can "persona owns disclosure language" (FR-009) be verified by static inspection of a documented constant or template, rather than runtime behavior alone? [Measurability, Spec §FR-009]
- [x] CHK020 - Can the persona's extraction schema be verified against each scripted fixture by direct comparison of expected vs. actual extracted fields? [Measurability, Spec §FR-009 + §FR-014]

## Scenario Coverage

- [x] CHK021 - Are requirements specified for persona behavior when the scripted fixture ends without reaching a disposition (truncated script, hangup before close)? [Coverage, Gap] → **RESOLVED-BY-FR-036 (rule #10) + FR-035 (`script_truncated`)**
- [x] CHK022 - Are requirements specified for persona behavior when the contact asks a question outside the persona's allowed-claim set (refusal, redirect, escalation)? [Coverage, Gap] → **RESOLVED-BY-FR-035 (`outside_allowed_claims`)**
- [x] CHK023 - Are requirements specified for persona behavior when the contact provides ambiguous role information (e.g., "I sometimes help with bookings")? [Coverage, Gap]
- [x] CHK024 - Are requirements specified for persona behavior when the contact provides a callback window outside the configured call window? [Coverage, Gap]
- [x] CHK025 - Are requirements specified for persona behavior when both signals (captured email AND callback request) are obtained, per the Q5 clarification (disposition is `interested_callback_requested`)? [Coverage, Spec §Clarifications]
- [x] CHK026 - Are requirements specified for persona behavior when no signals are obtained (no email, no callback, no clear interest) — does this map to `not_interested`, `needs_human_review`, or another disposition? [Coverage, Gap]

## Edge Case Coverage

- [x] CHK027 - Are requirements specified for handling a contact who explicitly identifies themselves as a resident or patient (PHI-collection risk; persona must refuse to engage on those topics and likely escalate)? [Edge Case, Gap]
- [x] CHK028 - Is the requirement to flag an unverifiable email and downgrade disposition (`interested_callback_requested` OR `needs_human_review`) precise about which downgrade applies when (which signals tip toward which path)? [Edge Case, Spec §Edge Cases]
- [x] CHK029 - Are requirements specified for persona behavior when the contact requests a recording be deleted or asserts a legal right (e.g., GDPR-style)? [Edge Case, Gap]
- [x] CHK030 - Are requirements specified for persona behavior when the contact's first utterance is a DNC statement (before disclosure is complete)? [Edge Case, Gap]

## Non-Functional Requirements

- [x] CHK031 - Are requirements specified for the persona's deterministic behavior across runs of the same scripted fixture (no randomization, no time-based branching)? [Gap, Spec §FR-009 + §SC-003]
- [x] CHK032 - Are requirements specified for the persona's response-time budget within SC-001's 60-second end-to-end window? [Gap, Spec §SC-001]

## Dependencies & Assumptions

- [x] CHK033 - Is the assumption that the persona runs against scripted fixtures in Slice 1 (no live model audio, no real-time AI integration) documented and aligned with FR-026's dry-run mandate? [Assumption, Spec §Assumptions + §FR-026]
- [x] CHK034 - Is the assumption that the future "real persona runtime" will satisfy the same boundary contract as the Slice 1 scripted persona explicit, and is the boundary contract named? [Assumption, Spec §Assumptions + §Constitution Alignment]

## Ambiguities & Conflicts

- [x] CHK035 - Is the persona's owner-of-extraction-schema responsibility (FR-009) reconciled with the normalized session result's field list (FR-014) — i.e., does the persona's extraction schema map 1:1 onto FR-014's fields, or are they distinct schemas? [Ambiguity, Spec §FR-009 + §FR-014]
- [x] CHK036 - Is the persona's "owns disposition rules" (FR-009) reconciled with FR-018's hard exclusions on which dispositions can emit follow-up tasks — when the persona's disposition rules would request a task for `not_interested`, does FR-018 override the persona, or vice versa? [Conflict, Spec §FR-009 + §FR-018]
- [x] CHK037 - Is the relationship between the persona's "escalation rules" and the eligibility module's "block decision" clear — both produce non-call outcomes; is there overlap or are their domains strictly disjoint? [Ambiguity, Spec §FR-004 + §FR-010]

---

## Addendum 2026-05-19 — Post-Remediation Coverage (FR-034 → FR-036)

The following items test the *new* FRs introduced during remediation. They validate that the persona's extraction schema, escalation reason codes, and disposition precedence are themselves well-specified.

### FR-034 — Persona extraction schema

- [x] CHK038 - Is FR-034's extraction schema field set complete (`captured_email`, `captured_email_unverified`, `callback_requested`, `preferred_callback_window`, `role_confidence`, `intent_classification`, `refusal_topics`)? Does it omit anything needed to determine disposition deterministically? [Completeness, Spec §FR-034]
- [x] CHK039 - Is the FR-034 `role_confidence` enum (`confident_decision_maker` / `confident_non_decision_maker` / `uncertain`) precise about edge cases (e.g., a contact who is a decision-maker but uncertain whether they want to engage)? [Ambiguity, Spec §FR-034]
- [x] CHK040 - Is the FR-034 `intent_classification` enum complete for every disposition the persona must produce? Is there a 1:1 or n:1 mapping from intent_classification to FR-013 dispositions? [Completeness, Spec §FR-034 + §FR-036]
- [x] CHK041 - Is FR-034's `refusal_topics` field defined operationally (a list of category labels, or arbitrary strings)? [Ambiguity, Spec §FR-034]
- [x] CHK042 - Is the mutual exclusivity of `captured_email` (verified only) vs. `captured_email_unverified` codified at the extraction-schema level, not just at the persisted-result level? [Consistency, Spec §FR-014 + §FR-034]

### FR-035 — Persona escalation reason codes

- [x] CHK043 - Is FR-035's enumeration of 9 reason codes (`uncertain_role`, `uncertain_intent`, `ambiguous_dnc`, `captured_email_invalid_no_callback`, `phi_collection_risk`, `legal_request`, `non_clinical_topic_escalation`, `outside_allowed_claims`, `script_truncated`) exhaustive for Slice 1, or are there scenarios that would require a free-form note in addition? [Completeness, Spec §FR-035]
- [x] CHK044 - Is the FR-035 "Slice 1 MUST NOT introduce free-form reasons" rule precise about how future slices may extend the enumeration (only by adding codes, not by replacing)? [Forward-compat, Spec §FR-035]
- [x] CHK045 - Is each FR-035 reason code traceable to a concrete trigger condition in the persona's logic (i.e., when does `phi_collection_risk` fire vs. `non_clinical_topic_escalation`)? [Clarity, Spec §FR-035]

### FR-036 — Persona disposition rule precedence

- [x] CHK046 - Is FR-036's 10-rule precedence list exhaustive — does it cover every combination of FR-034 extraction signals? [Completeness, Spec §FR-036 + §FR-034]
- [x] CHK047 - Is FR-036 rule #4 (verified email AND callback → `interested_callback_requested`) consistent with the Q5 Clarification's wording about email retention in the callback task payload? [Consistency, Spec §FR-036 + §Clarifications]
- [x] CHK048 - Is FR-036 rule #7 (unverified email, no callback → `needs_human_review` with `captured_email_invalid_no_callback`) consistent with the Edge Case "Email captured but invalid format" (which says fall back to `interested_callback_requested` OR `needs_human_review`)? [Consistency, Spec §FR-036 + §Edge Cases]
- [x] CHK049 - Is FR-036's "first match wins" precedence precise about what happens when two extraction signals would each match different rules (does priority 1 always shut out priority 2+)? [Clarity, Spec §FR-036]
- [x] CHK050 - Is FR-036 rule #10 (`script_truncated`) a catch-all for "no clear signal" or specifically for "the conversation fixture ended without final disposition information"? [Ambiguity, Spec §FR-036]
- [x] CHK051 - Is FR-036's determinism mandate ("no randomness, no wall-clock, no external IO") testable by code inspection / unit-test fuzz of the disposition_rules module? [Measurability, Spec §FR-036]
- [x] CHK052 - Is the FR-036 precedence list consistent with the persona contract's restatement (contracts/persona.md) — i.e., do both list the same 10 rules in the same order? [Consistency, Spec §FR-036 + Contracts §persona.md]
