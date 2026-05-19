# Acceptance & Success-Criteria Quality Checklist: Slice 1 — Mock Call, Mock CRM

**Purpose**: Validate the quality, clarity, completeness, and measurability of acceptance scenarios and success criteria. Unit tests for the *requirements writing* in user stories, edge cases, and Success Criteria — NOT for the implementation.

**Created**: 2026-05-19
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [ ] CHK001 - Does at least one Success Criterion address each of: end-to-end loop (SC-001), eligibility blocking (SC-002), disposition coverage (SC-003), callback-task content (SC-004), idempotency (SC-005), false-positive prevention (SC-006), operator readability (SC-007), contract symmetry (SC-008), and module isolation (SC-009)? [Completeness, Spec §SC-001 through §SC-009]
- [ ] CHK002 - Are acceptance scenarios provided for each priority user story (Story 1 P1, Story 2 P2, Story 3 P2, Story 4 P3)? [Completeness, Spec §Story 1–4]
- [ ] CHK003 - Are acceptance scenarios provided (or aggregated via SC-003) for every disposition in FR-013's enum (`interested_callback_requested`, `interested_email_captured`, `not_interested`, `call_back_later`, `wrong_number`, `no_answer`, `voicemail`, `do_not_call`, `needs_human_review`, `failed`)? [Coverage, Spec §FR-013 + §SC-003]
- [ ] CHK004 - Are acceptance scenarios provided for each duplicate-event path that Story 3 enumerates (duplicate connected/completed, duplicate callback-requested)? [Completeness, Spec §Story 3]
- [ ] CHK005 - Is an acceptance scenario provided for the blocked-by-eligibility outcome at the Success Criteria level (not just within Story 2 narrative)? [Gap, Spec §SC-002]
- [ ] CHK006 - Are acceptance scenarios provided for the captured-email-AND-callback edge case clarified in Q5? [Gap, Spec §Clarifications]

## Requirement Clarity

- [ ] CHK007 - Is SC-001's "under 60 seconds end-to-end" defined precisely (timer start at CLI invocation, timer stop at last artifact written; does it include fixture-load time)? [Clarity, Spec §SC-001]
- [ ] CHK008 - Is "developer laptop" in SC-001 specified with a minimum hardware/OS profile, or is the metric a target-with-disclosed-environment? [Ambiguity, Spec §SC-001]
- [ ] CHK009 - Is SC-007's "explain the outcome without consulting source code" defined with a concrete artifact-walkthrough scope (which fields the operator must be able to point to)? [Clarity, Spec §SC-007]
- [ ] CHK010 - Is the phrase "scripted fixture" in SC-003 defined precisely (a deliverable artifact, one per disposition, with a named location)? [Ambiguity, Spec §SC-003]
- [ ] CHK011 - Is SC-009's "exercised in isolation against fixtures without instantiating the others" defined operationally (each module's interface MUST be satisfiable by a stub that requires no dependency on other modules)? [Clarity, Spec §SC-009]

## Requirement Consistency

- [ ] CHK012 - Is SC-003 ("every supported disposition can be reached via a scripted fixture") consistent with FR-013's enum — does the fixture set cover all 10 dispositions PLUS the blocked-by-eligibility outcome? [Consistency, Spec §SC-003 + §FR-013]
- [ ] CHK013 - Is SC-005 ("100% of duplicate mock provider events redelivered for the same session leave state...unchanged") consistent with FR-020's audit-record requirement (conflicting events are recorded — does writing an audit row count as "state changed")? [Consistency, Spec §SC-005 + §FR-020]
- [ ] CHK014 - Are the Story 1 acceptance-scenario disposition values (`interested_callback_requested`, `interested_email_captured`, `needs_human_review`) all present in FR-013's enum with the exact same string spelling? [Consistency, Spec §Story 1 + §FR-013]
- [ ] CHK015 - Are the Story 2 acceptance-scenario block-reason names (DNC, call-window, max-attempts, missing-phone) consistent with the FR-004 rule names? [Consistency, Spec §Story 2 + §FR-004]
- [ ] CHK016 - Are the Story 3 acceptance-scenario event types (`no_answer`, `voicemail`, `failed`) consistent with the FR-006 event-emission list? [Consistency, Spec §Story 3 + §FR-006]
- [ ] CHK017 - Is SC-004's "callback task payload includes the preferred callback window" consistent with the Q5 clarification (callback task payload also includes captured email when both signals are present)? [Consistency, Spec §SC-004 + §Clarifications]

## Acceptance Criteria Quality

- [ ] CHK018 - Is SC-008 (forward-looking Slice 2 reuse) verifiable at Slice 1 release time, or is it deferred — and is the deferral explicitly acknowledged with a Slice 1 placeholder check? [Measurability, Spec §SC-008]
- [ ] CHK019 - Is SC-009 (each module exercisable in isolation) phrased as a testable property a CI gate can run against? [Measurability, Spec §SC-009]
- [ ] CHK020 - Is SC-002's "100% of records that fail any one of the configured eligibility rules are blocked" measurable across a finite fixture set, and is that fixture set enumerated as a deliverable? [Measurability, Spec §SC-002]
- [ ] CHK021 - Is SC-006's "0 false connected-call activities" verifiable by static inspection of exported artifacts (no implementation runtime check required)? [Measurability, Spec §SC-006]
- [ ] CHK022 - Are the "Given / When / Then" structures in each acceptance scenario specific enough that two independent reviewers would write the same fixture? [Measurability, Spec §Story 1–3]

## Scenario Coverage

- [ ] CHK023 - Are acceptance scenarios provided for the `call_back_later` disposition (distinct from `interested_callback_requested`)? [Gap, Spec §FR-013]
- [ ] CHK024 - Are acceptance scenarios provided for the `not_interested` disposition (distinct from `do_not_call`)? [Gap, Spec §FR-013]
- [ ] CHK025 - Are acceptance scenarios provided for the `voicemail` disposition's write-back shape? [Coverage, Spec §Story 3]
- [ ] CHK026 - Are acceptance scenarios provided for the `failed` disposition's persona-version handling (was the persona ever instantiated; is the version recorded)? [Coverage, Spec §FR-011 + §Story 3]
- [ ] CHK027 - Are acceptance scenarios provided for the call-window-expires-mid-call edge case? [Coverage, Spec §Edge Cases]
- [ ] CHK028 - Are acceptance scenarios provided for the persona-stated mid-call DNC (the path that produces `do_not_call` disposition, callable_status → `dnc`, no follow-up task)? [Coverage, Spec §Edge Cases + §Clarifications]

## Edge Case Coverage

- [ ] CHK029 - Are acceptance scenarios provided for malformed timezone handling (default applied; recorded in eligibility decision)? [Coverage, Spec §Edge Cases]
- [ ] CHK030 - Are acceptance scenarios provided for invalid-format captured-email downgrade behavior? [Coverage, Spec §Edge Cases]
- [ ] CHK031 - Are acceptance scenarios provided for unknown-event-type handling? [Coverage, Spec §Edge Cases]
- [ ] CHK032 - Are acceptance scenarios provided for the attempt-count-already-at-max path? [Coverage, Spec §Edge Cases]

## Non-Functional Requirements

- [ ] CHK033 - Are the timing target (SC-001's 60-second budget) and observability targets (operator readability, SC-007) defined as testable thresholds rather than aspirations? [Measurability, Spec §SC-001 + §SC-007]
- [ ] CHK034 - Are demo-readiness criteria (FR-026's dry-run mode + Assumptions' "Demo posture") tied to a specific SC or are they implicit? [Gap, Spec §FR-026 + §Assumptions]

## Dependencies & Assumptions

- [ ] CHK035 - Is the dependency on a deterministic scripted fixture set (one per disposition) acknowledged as a Slice 1 deliverable that gates SC-003 verification? [Assumption, Spec §SC-003]
- [ ] CHK036 - Is the assumption that "a clean local state store" (Story 1 Given clause) is reproducible by a documented reset command or fresh fixture load? [Assumption, Spec §Story 1]

## Ambiguities & Conflicts

- [ ] CHK037 - Is Story 2's "no session is created, OR a session is created in a 'blocked' terminal state with no mock provider events" disambiguated — which is the intended Slice 1 behavior? [Ambiguity, Spec §Story 2]
- [ ] CHK038 - Is the relationship between SC-001's 60-second budget and the persona's potentially long scripted conversations precise — is the budget the worst case across all fixtures or only the happy path? [Ambiguity, Spec §SC-001]
- [ ] CHK039 - Is the Story 4 acceptance for "exported task payload describes a review-style follow-up" reconciled with FR-015's "Task-like callback or review action payload" terminology (same artifact, different name)? [Ambiguity, Spec §Story 4 + §FR-015]

---

## Addendum 2026-05-19 — Post-Remediation Coverage (SC-003 11th disposition + Q5 case)

- [ ] CHK040 - Is SC-003's 11-disposition enumeration consistent with FR-013's 11-value enum (both list `blocked` as the 11th value, with the carve-out that `blocked` is reachable via an eligibility-rule failure rather than a scripted-conversation fixture)? [Consistency, Spec §SC-003 + §FR-013]
- [ ] CHK041 - Is SC-003's "produces the per-disposition write-back shape defined in FR-031" measurable as a fixture-set property that traverses every row of FR-031's table at least once? [Measurability, Spec §SC-003 + §FR-031]
- [ ] CHK042 - Is the Q5 Clarification case (captured email AND callback request → `interested_callback_requested` with email in callback task payload) covered by a dedicated SC OR by an enumerated acceptance scenario in Story 1, or only by the FR-013 + FR-030 + FR-036 cross-reference? [Gap, Spec §Clarifications]
