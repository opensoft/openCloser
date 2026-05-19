# Eligibility Requirements Quality Checklist: Slice 1 — Mock Call, Mock CRM

**Purpose**: Validate the quality, clarity, and completeness of eligibility-gate requirements (the six rules, configuration surface, blocked outcomes, mid-call DNC transition). Unit tests for the *requirements*, not for the implementation.

**Created**: 2026-05-19
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [ ] CHK001 - Are all six eligibility rules (phone presence, usable timezone, call window, DNC flag, attempt-count below max, callable-status) individually named, ordered, and described in FR-004? [Completeness, Spec §FR-004]
- [ ] CHK002 - Is the configured call window's structure specified (start hour, end hour, weekday applicability, timezone source)? [Completeness, Spec §FR-004 + §Assumptions]
- [ ] CHK003 - Is the max-attempts default value (5) named, with the override mechanism (configuration surface) referenced? [Completeness, Spec §Assumptions]
- [ ] CHK004 - Is the default-timezone fallback value or configuration source specified? [Completeness, Spec §Assumptions]
- [ ] CHK005 - Are the persisted fields of an Eligibility Decision (rule names list, pass/fail per rule, blocking reason set, decision timestamp, references) enumerated? [Completeness, Spec §FR-004]
- [ ] CHK006 - Is the blocked-by-eligibility disposition value explicitly named and aligned with FR-013's enum (i.e., is `blocked` itself a disposition, or is the value something else)? [Conflict, Spec §FR-012 + §FR-013] → **RESOLVED-BY-Clarifications (Phase 1 #2) + FR-013 (`blocked` added as 11th value)**
- [ ] CHK007 - Is the configuration surface itself named (a single config file, environment vars, a CLI flag, or other) for call window, max attempts, and default timezone? [Gap]

## Requirement Clarity

- [ ] CHK008 - Is "current local time within the configured call window" defined precisely (inclusive vs. exclusive boundaries; what happens exactly at the boundary minute)? [Clarity, Spec §FR-004]
- [ ] CHK009 - Is "phone presence" defined precisely (non-empty string, E.164 format, presence of a usable digit count, valid country code)? [Ambiguity, Spec §FR-004]
- [ ] CHK010 - Is "usable timezone" defined (IANA name only, any parseable string, or resolvable to a UTC offset by some library)? [Ambiguity, Spec §FR-004]
- [ ] CHK011 - Is the max-attempts comparison semantics specified (block when `attempt_count >= max` vs. `> max`)? [Clarity, Spec §FR-004 + §FR-021]
- [ ] CHK012 - Is "callable-status equals `ready`" precisely tested against the FR-002 enum (does eligibility look at exactly that field with exactly that string match)? [Clarity, Spec §FR-002 + §FR-004 + §Clarifications]

## Requirement Consistency

- [ ] CHK013 - Does the spec consistently state that blocked-by-eligibility runs (a) do NOT increment `attempt_count`, (b) do NOT emit a Phone Call-like activity, and (c) do NOT create a connected-call session — across FR-005, FR-017, FR-021, and the Clarifications log? [Consistency, Spec §FR-005 + §FR-017 + §FR-021 + §Clarifications]
- [ ] CHK014 - Do the eligibility-block edge cases listed in Story 2 acceptance map one-to-one with the FR-004 rule list (every Story 2 scenario corresponds to a named rule)? [Consistency, Spec §Story 2 + §FR-004]
- [ ] CHK015 - Is the "callable_status='dnc'" eligibility-block path consistent with the "DNC flag set" eligibility-block path — do both yield the same blocked disposition string, the same blocking-reason name, and the same write-back shape? [Consistency, Spec §Clarifications + §FR-004]
- [ ] CHK016 - Is FR-005's "MUST NOT increment attempt count" consistent with FR-021's clarified "Blocked-by-eligibility runs MUST NOT increment `attempt_count`"? [Consistency, Spec §FR-005 + §FR-021]

## Acceptance Criteria Quality

- [ ] CHK017 - Can SC-002's "100% of records that fail any one of the configured eligibility rules are blocked" be measured deterministically against a finite, enumerated fixture set? [Measurability, Spec §SC-002]
- [ ] CHK018 - Is "the failing rule is named in the persisted decision" verifiable by inspection of the exported Eligibility Decision JSON alone? [Measurability, Spec §SC-002]
- [ ] CHK019 - Are the individual rule pass/fail outcomes in the Eligibility Decision specified precisely enough to support unit-level test assertions per rule? [Measurability, Spec §FR-004]

## Scenario Coverage

- [ ] CHK020 - Are requirements specified for an Eligibility Decision when multiple rules fail simultaneously — does the decision list ALL failing rules, or short-circuit on the first? [Coverage, Gap]
- [ ] CHK021 - Are requirements specified for re-evaluating eligibility within a single run when the call-window expires mid-call (Edge Case)? [Coverage, Spec §Edge Cases]
- [ ] CHK022 - Are requirements specified for the case where the queue record's timezone is technically present but unparseable (vs. missing entirely)? [Coverage, Spec §Edge Cases]
- [ ] CHK023 - Are requirements specified for the case where the configured call window is itself missing or malformed? [Coverage, Gap]
- [ ] CHK024 - Are requirements specified for the case where `attempt_count` is missing or negative on the queue record? [Coverage, Gap]
- [ ] CHK025 - Are requirements specified for the case where the DNC flag is non-boolean (e.g., a string "true", null, or a "soft" flag)? [Coverage, Gap]

## Edge Case Coverage

- [ ] CHK026 - Is the requirement to record the default-timezone fallback in the Eligibility Decision explicit, including which field of the decision captures both the original record value and the default that was substituted? [Edge Case, Spec §Edge Cases]
- [ ] CHK027 - Is the behavior at `attempt_count == max` (block before call) precisely distinguished from `attempt_count == max-1` (allow, will become max after this call)? [Edge Case, Spec §Edge Cases]
- [ ] CHK028 - Is the call-window-expires-mid-call behavior stated precisely (in-flight call continues; no new calls placed; what is recorded in the Eligibility Decision for the in-flight call)? [Edge Case, Spec §Edge Cases]
- [ ] CHK029 - Are requirements specified for daylight-saving-time transitions that move the local time in or out of the call window mid-conversation? [Edge Case, Gap]

## Dependencies & Assumptions

- [ ] CHK030 - Is the assumption that DNC sources are limited to the queue record + persona-stated mid-call opt-out (no external DNC list) explicit, and is the rationale stated? [Assumption, Spec §Assumptions]
- [ ] CHK031 - Is the dependency on a "configuration surface" for call window / max attempts / default timezone acknowledged as a Slice 1 deliverable rather than an external pre-existing concern? [Assumption, Gap]

## Ambiguities & Conflicts

- [ ] CHK032 - Is there a clearly named disposition for a blocked-by-eligibility outcome — does FR-012's "blocked" final disposition use the literal string `blocked`, and is this in the FR-013 enum? [Conflict, Spec §FR-012 + §FR-013] → **RESOLVED-BY-FR-013 (`blocked` is the 11th value)**
- [ ] CHK033 - Is the relationship between FR-004(f) ("callable_status = ready") and the DNC-flag rule (FR-004(d)) clarified — if a record has `dnc_flag=true` AND `callable_status='dnc'`, do both rules fire (two blocking reasons) or does one supersede the other? [Ambiguity, Spec §FR-004 + §Clarifications]
- [ ] CHK034 - Is the relationship between Story 2's "no session is created, OR a session is created in a 'blocked' terminal state" disambiguated — which is the intended Slice 1 behavior? [Ambiguity, Spec §Story 2] → **RESOLVED-BY-Clarifications (Phase 1 #3) + FR-005 (always create blocked-state session)**
