# Safety & Compliance Requirements Quality Checklist: Slice 1 — Mock Call, Mock CRM

**Purpose**: Validate the quality, clarity, and completeness of safety, compliance, disclosure, DNC, call-window, max-attempts, and human-handoff requirements. Unit tests for the *requirements*, not for the implementation.

**Created**: 2026-05-19
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 - Are the persona's mandatory disclosure statements (it is an AI assistant; calling on behalf of Medx) specified with exact wording, a paraphrase-allowed list of variants, or boundary constraints on what wording must include? [Completeness, Spec §FR-010]
- [x] CHK002 - Are the persona's allowed claim categories enumerated (what it MAY say about Medx, services, pricing, scheduling) and the disallowed claim categories enumerated (what it MUST NOT say)? [Gap, Spec §FR-009]
- [x] CHK003 - Is the prohibition on collecting PHI specified with concrete examples of disallowed data classes (medications, diagnoses, treatment plans, resident names, room numbers)? [Completeness, Spec §FR-010]
- [x] CHK004 - Are the persona's DNC-honoring trigger phrases or trigger criteria specified (literal phrases, intent-classification heuristics, threshold for "explicit opt-out")? [Gap, Spec §FR-010]
- [x] CHK005 - Are the conditions for `needs_human_review` enumerated (uncertain role, uncertain intent, ambiguous DNC, captured-email-invalid downgrade path, others)? [Completeness, Spec §FR-010 + §Edge Cases] → **RESOLVED-BY-FR-035 (9-code enumeration)**
- [x] CHK006 - Is the requirement to "MUST respect a configured local call window and a maximum-attempts limit BEFORE placing a mock call" reflected in the eligibility rules and traceable to specific FRs? [Completeness, Spec §Constitution Alignment + §FR-004]
- [x] CHK007 - Are the persona's escalation rules (which scenarios trigger `needs_human_review` with which reason codes) enumerated as a finite set? [Gap, Spec §FR-010 + §FR-014] → **RESOLVED-BY-FR-035**

## Requirement Clarity

- [x] CHK008 - Is "non-clinical" defined with concrete examples of out-of-scope topics, or left as a reviewer-judgment phrase? [Ambiguity, Spec §FR-010]
- [x] CHK009 - Is "immediately" in "honor opt-out / do-not-call statements immediately" quantified (next persona turn, before any further sales statement, within N words)? [Clarity, Spec §FR-010]
- [x] CHK010 - Is "stated reason" for human-review escalation defined as a free-form string, an enumerated reason code, or both (code + free-form note)? [Ambiguity, Spec §FR-010 + §FR-014]
- [x] CHK011 - Is "uncertain or unsafe outcomes" defined precisely enough to make the persona's escalation rules deterministic across runs of the same fixture? [Clarity, Spec §FR-010]

## Requirement Consistency

- [x] CHK012 - Are the DNC-mid-call edge case requirements (set `dnc_flag=true`, set `callable_status='dnc'`, queue-status write-back reflects transition, final disposition `do_not_call`, no follow-up task) consistent across Edge Cases, FR-018, the Clarifications log, and the Constitution Alignment's "persist the DNC signal" mandate? [Consistency, Spec §Edge Cases + §FR-018 + §Clarifications]
- [x] CHK013 - Is "wrong number" handling consistent with "DNC stated mid-conversation" handling in terms of sales-flow termination, write-back shape, and follow-up-task exclusion (per FR-018)? [Consistency, Spec §Edge Cases + §FR-018]
- [x] CHK014 - Are FR-018's hard exclusions (no callback/review task for `not_interested`, `wrong_number`, `do_not_call`, `failed` unless persona rules explicitly say otherwise) consistent with each disposition's acceptance scenarios and edge cases? [Consistency, Spec §FR-018]
- [x] CHK015 - Is the safety mandate "persona MUST NOT collect resident or patient health information" consistent with the data model's `captured_email` field (i.e., is email collection explicitly NOT considered PHI here, and is the rationale stated)? [Consistency, Spec §FR-010 + §FR-014]

## Acceptance Criteria Quality

- [x] CHK016 - Can "MUST disclose at the start of every connected conversation" be verified deterministically against a scripted transcript fixture (e.g., a regex on the first persona turn)? [Measurability, Spec §FR-010]
- [x] CHK017 - Is the "stated reason" for `needs_human_review` measurable from the exported session-result JSON's `human_review_reason` field alone? [Measurability, Spec §FR-014]
- [x] CHK018 - Is "MUST honor DNC / opt-out statements immediately" testable against a fixture that asserts no persona output occurs after the DNC trigger? [Measurability, Spec §FR-010]

## Scenario Coverage

- [x] CHK019 - Are requirements specified for a connected call where the contact hangs up before the persona's disclosure completes? [Coverage, Gap]
- [x] CHK020 - Are requirements specified for a contact who states DNC before the persona's disclosure completes? [Coverage, Gap]
- [x] CHK021 - Are requirements specified for a contact who asks a clinical question (e.g., medication advice) — persona refusal, redirect, or escalation? [Coverage, Gap]
- [x] CHK022 - Are requirements specified for a connected contact who self-identifies as a resident, patient, or family-of-resident (PHI-collection risk path)? [Coverage, Gap]
- [x] CHK023 - Are requirements specified for a contact whose preferred callback window falls outside the configured call window? [Coverage, Gap]
- [x] CHK024 - Are requirements specified for handling a connected call that lasts longer than a reasonable threshold (timeout, hangup, escalation)? [Coverage, Gap]

## Edge Case Coverage

- [x] CHK025 - Is the "call window expires mid-call" requirement specific about whether the persona modifies its close, abruptly hangs up, or simply continues unmodified to natural end? [Edge Case, Spec §Edge Cases]
- [x] CHK026 - Is the "email captured but invalid format" requirement precise about which downgrade applies when (`interested_callback_requested` vs. `needs_human_review`)? [Edge Case, Spec §Edge Cases]
- [x] CHK027 - Are requirements specified for ambiguous DNC signals (e.g., "don't call this number again" vs. "I'm busy right now" vs. "we'll get back to you")? [Edge Case, Gap]
- [x] CHK028 - Are requirements specified for cases where the persona detects a possible legal/regulatory ask (e.g., contact requests a recording be deleted)? [Edge Case, Gap]
- [x] CHK029 - Are requirements specified for a contact who provides verbal opt-out for a different prospect (e.g., "stop calling my brother")? [Edge Case, Gap]

## Non-Functional Requirements

- [x] CHK030 - Are requirements specified for redaction of any PHI-adjacent text accidentally captured in the transcript file (per FR-024's "minimize sensitive data")? [Coverage, Spec §FR-024]
- [x] CHK031 - Are requirements specified for an audit trail that proves disclosure was made on every connected conversation (independent of the transcript file)? [Gap, Spec §FR-010]

## Dependencies & Assumptions

- [x] CHK032 - Is the assumption that the persona's version, recorded on every session (FR-011), provides sufficient audit traceability stated and rationalized? [Assumption, Spec §FR-011]
- [x] CHK033 - Is the assumption that no real outbound traffic occurs in Slice 1 (FR-026 dry-run mandate) tied to a hard safety guarantee, not just a default mode? [Assumption, Spec §FR-026 + §Assumptions]
- [x] CHK034 - Is the assumption that the persona, not the orchestrator, is the locus of safety decisions (disclosure, DNC honoring, escalation) explicit and traceable to specific FRs? [Assumption, Spec §FR-009 + §FR-010]

## Ambiguities & Conflicts

- [x] CHK035 - Is there an explicit conflict-resolution rule when the persona's disposition rules (FR-009 — persona owns) would emit a task payload for `do_not_call` (FR-018 forbids)? Which authority wins? [Conflict, Spec §FR-009 + §FR-018]
- [x] CHK036 - Is the Constitution Alignment's "MUST honor opt-out / do-not-call statements immediately and persist the DNC signal" reconciled with the persona's ownership of disposition rules — i.e., is DNC honoring a hard system invariant or a persona-configurable behavior? [Conflict, Spec §Constitution Alignment + §FR-009]
- [x] CHK037 - Is the phrase "review-style follow-up" (Story 4 acceptance #2) defined the same as "review action payload" (FR-015) and "review-style task payload" (Story 1 acceptance #3)? [Ambiguity, Spec §Story 1 + §Story 4 + §FR-015]

---

## Addendum 2026-05-19 — Post-Remediation Coverage (FR-035 reason codes + transcript accepted-risk)

- [x] CHK038 - Is FR-035's reason-code enumeration's safety value clear — does every code map to a concrete operator-visible follow-up action (escalation queue, review task subject, etc.)? [Clarity, Spec §FR-035]
- [x] CHK039 - Is the Transcript Retention Assumption's "accepted Slice 1 risk" claim explicit about WHAT risk is accepted (writing the full scripted transcript to disk) and WHY (persona non-clinical, no PHI by construction)? [Clarity, Spec §Assumptions]
- [x] CHK040 - Is the deferred Slice 2 redaction layer (Assumptions §Transcript retention) tied to a concrete future-slice deliverable, or only mentioned aspirationally? [Forward-compat, Spec §Assumptions]
