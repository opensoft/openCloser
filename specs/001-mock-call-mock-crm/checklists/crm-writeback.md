# Mock CRM Write-back Requirements Quality Checklist: Slice 1 — Mock Call, Mock CRM

**Purpose**: Validate the quality, clarity, and completeness of mock CRM adapter requirements — Phone Call-like activity payloads, queue-status update payloads, Task-like payloads, contract symmetry with the future Dataverse adapter, and FR-018 exclusions. Unit tests for the *requirements*, not for the implementation.

**Created**: 2026-05-19
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 - Is the Phone Call-like activity payload's required field set enumerated (session reference, queue-item reference, started/ended timestamps, mock_provider_call_id, final disposition, summary, persona version)? [Gap, Spec §FR-015] → **RESOLVED-BY-FR-028**
- [x] CHK002 - Is the queue-status update payload's required field set enumerated (queue-item reference, previous status, new status, transition timestamp, transition reason)? [Gap, Spec §FR-015] → **RESOLVED-BY-FR-029**
- [x] CHK003 - Is the Task payload's required field set fully enumerated (subject, due-date OR preferred callback window, reason code, references to session and queue item, captured email when present per Q5 clarification, persona version)? [Completeness, Spec §FR-015 + §Clarifications]
- [x] CHK004 - Is the contract-symmetry requirement (mock CRM adapter shape == future Dataverse adapter shape) specified with a named list of operations / methods the adapter MUST expose? [Gap, Spec §FR-016] → **RESOLVED-BY-FR-033**
- [x] CHK005 - Is the per-disposition write-back shape mapping specified (which disposition produces which combination of activity / queue-status / task payloads)? [Gap, Spec §FR-015 + §FR-018] → **RESOLVED-BY-FR-031**
- [x] CHK006 - Are the write-back requirements specified for the case where multiple write-back payloads are produced for a single session (e.g., interested_callback_requested → all three)? [Completeness, Spec §Story 1]
- [x] CHK007 - Are the write-back requirements specified for the persona-version field's propagation through every payload kind (or its omission)? [Gap, Spec §FR-011 + §FR-015] → **RESOLVED-BY-FR-028/FR-030**

## Requirement Clarity

- [x] CHK008 - Is "Phone Call-like activity" defined precisely (which Dataverse entity it mirrors, which fields map to which Dataverse field) to make the contract-symmetry claim verifiable? [Ambiguity, Spec §FR-015 + §FR-016]
- [x] CHK009 - Is "queue-status update payload" defined as a delta (old → new) or a full new-status snapshot? [Ambiguity, Spec §FR-015]
- [x] CHK010 - Is "Task-like callback or review action" defined with explicit subject/owner/due-date semantics, or are these left to the persona's escalation rules? [Ambiguity, Spec §FR-015]
- [x] CHK011 - Is "presents the same conceptual contract" (FR-016) defined as a named interface, a method-signature list, or a reviewer-judgment phrase? [Clarity, Spec §FR-016]
- [x] CHK012 - Is the relationship between "persists" and "exports" in FR-015 specified precisely — does the adapter both write to internal state AND emit a JSON artifact, or is the JSON artifact the canonical persisted representation? [Ambiguity, Spec §FR-015 + §FR-023]

## Requirement Consistency

- [x] CHK013 - Is FR-017 (no Phone Call-like activity for blocked sessions) consistent with FR-015 ("queue-status update payload always when a record is processed") — i.e., are blocked records still expected to emit a queue-status update? [Consistency, Spec §FR-015 + §FR-017]
- [x] CHK014 - Is FR-018 (exclude task payloads for `not_interested` / `wrong_number` / `do_not_call` / `failed`) consistent with the persona's authority over disposition rules per FR-009, and is the precedence rule explicit? [Consistency, Spec §FR-009 + §FR-018]
- [x] CHK015 - Are the disposition → write-back shape mappings consistent between Story 1 (interested outcomes produce all three payload kinds), Story 3 (`no_answer` / `voicemail` / `failed` paths), and FR-015–FR-018? [Consistency, Spec §Story 1 + §Story 3 + §FR-015]
- [x] CHK016 - Is the DNC-mid-call edge case's write-back behavior (queue-status payload reflects transition to `dnc`; no follow-up task) consistent with FR-018 (forbids tasks for `do_not_call`) and the Constitution Alignment's "MUST persist the DNC signal"? [Consistency, Spec §Edge Cases + §FR-018 + §Clarifications]
- [x] CHK017 - Is the "no Interaction Core / eligibility / persona / transport code may depend on mock-specific shapes" (FR-016) consistent with FR-015's allowance to "persist and export" mock payloads (i.e., is "depend on shape" understood as compile-time vs. runtime)? [Consistency, Spec §FR-015 + §FR-016]

## Acceptance Criteria Quality

- [x] CHK018 - Is SC-008 (contract symmetry across slices) stated with verifiable Slice 1 criteria (e.g., "named interface documented and reviewed") rather than deferred entirely to Slice 2 plan time? [Measurability, Spec §SC-008]
- [x] CHK019 - Can the requirement "no Phone Call-like activity is emitted for any blocked record" (SC-002) be verified by static inspection of the exported artifacts after a fixture run? [Measurability, Spec §SC-002]
- [x] CHK020 - Is "Task payload for interested or uncertain outcomes" measurable per-disposition with an explicit which-disposition-triggers-which-task-type table? [Measurability, Spec §FR-018 + §SC-003]
- [x] CHK021 - Is the contract-symmetry property (SC-008) testable at Slice 1 release time (e.g., via an interface-definition file reviewed against the future Dataverse adapter's intended methods)? [Measurability, Spec §SC-008]

## Scenario Coverage

- [x] CHK022 - Are requirements specified for write-back behavior when the persona produces a disposition not in FR-013's enum (defensive case)? [Coverage, Gap]
- [x] CHK023 - Are requirements specified for a session that finalizes mid-call due to call-window expiry (does it emit a Phone Call-like activity, and what is the disposition)? [Coverage, Spec §Edge Cases]
- [x] CHK024 - Are requirements specified for the queue-status update payload's new-status value when the session ends in `needs_human_review` (does callable_status change, and to what)? [Coverage, Gap]
- [x] CHK025 - Are requirements specified for the queue-status update payload's new-status value for each disposition in FR-013's enum? [Coverage, Gap] → **RESOLVED-BY-FR-032**
- [x] CHK026 - Are requirements specified for write-back behavior when the same queue item is re-run after a non-terminal disposition (e.g., a previous `no_answer`)? [Coverage, Gap]

## Edge Case Coverage

- [x] CHK027 - Are requirements specified for the case where a Task payload would carry both a `preferred_callback_window` and a captured email (per the Q5 clarification — both fields populated, disposition `interested_callback_requested`)? [Edge Case, Spec §Clarifications]
- [x] CHK028 - Are requirements specified for write-back idempotency at the adapter layer (must the adapter itself no-op on duplicate inputs, or only its upstream callers, per FR-019)? [Edge Case, Spec §FR-019]
- [x] CHK029 - Are requirements specified for the case where the adapter is asked to emit a write-back for a session that does not exist in local state (defensive boundary case)? [Edge Case, Gap]
- [x] CHK030 - Are requirements specified for the write-back shape on a `failed` event that fires before any `connected` event (no real conversation occurred — does the activity payload include a summary and persona version)? [Edge Case, Gap]

## Non-Functional Requirements

- [x] CHK031 - Are requirements specified for write-back ordering guarantees (must activity → queue-status → task occur in a specific order, or are they independent)? [Gap, Spec §FR-015]
- [x] CHK032 - Are requirements specified for the adapter's failure semantics — what happens if persistence succeeds but artifact export fails (or vice versa)? [Gap, Spec §FR-015 + §FR-023]

## Dependencies & Assumptions

- [x] CHK033 - Is the assumption that the local queue and the mock CRM adapter together stand in for the CRM control plane stated as a Slice 1-only constraint with no follow-on UI / campaign workflow? [Assumption, Spec §Assumptions + §Constitution Alignment]
- [x] CHK034 - Is the assumption that FR-016's "no Interaction Core code depends on mock-specific shapes" is testable by code inspection rather than runtime behavior alone documented? [Assumption, Spec §FR-016]

## Ambiguities & Conflicts

- [x] CHK035 - Is the relationship between the mock CRM adapter's "persisted" output and its "exported artifact" output disambiguated — is the JSON artifact the canonical output, a derived view of internal state, or a duplicate write? [Ambiguity, Spec §FR-015 + §FR-023]
- [x] CHK036 - Is FR-018's "unless the persona / disposition rules explicitly call for one (e.g., `needs_human_review`)" reconciled with FR-009's "persona owns disposition rules" — i.e., is the persona allowed to override FR-018 for `not_interested` / `wrong_number` / `do_not_call` / `failed`, or are those four absolute? [Conflict, Spec §FR-009 + §FR-018]
- [x] CHK037 - Is the queue-status update payload's content for a session that creates no Phone Call-like activity (blocked-by-eligibility) precisely defined — what is the new status value, and what is the transition reason? [Ambiguity, Spec §FR-015 + §FR-017]

---

## Addendum 2026-05-19 — Post-Remediation Coverage (FR-028 → FR-032)

The following items test the *new* FRs introduced during remediation. They validate that the additions are themselves well-written, consistent, and complete.

### FR-028 — Phone Call activity payload field list

- [x] CHK038 - Is FR-028's required field set complete (session_id, queue_item_id, mock_provider_call_id, persona_version, final_disposition, summary, started_at, ended_at)? Does the list omit anything a Dataverse Phone Call entity would need? [Completeness, Spec §FR-028]
- [x] CHK039 - Is FR-028's "MUST NOT be emitted for `blocked` sessions" cross-referenced with FR-017's identical exclusion (one is normative, the other is redundant)? [Consistency, Spec §FR-017 + §FR-028]
- [x] CHK040 - Is FR-028's `summary` field defined as required (no nullable) for every disposition that produces a Phone Call activity, including dispositions where no real conversation occurred (`no_answer`, `voicemail`, `failed`)? [Ambiguity, Spec §FR-028]

### FR-029 — Queue-status update payload field list

- [x] CHK041 - Is FR-029's `transition_reason` defined precisely (free-form string vs. enumerated code)? Is the reason format the same across allowed-session and blocked-session transitions? [Ambiguity, Spec §FR-029]
- [x] CHK042 - Is FR-029's "exactly once per processed queue-item ID" measurable as a SQLite-level uniqueness constraint on `session_id`? [Measurability, Spec §FR-029]
- [x] CHK043 - Is the FR-029 `previous_status` value for a blocked-by-eligibility session defined (it's whatever the record had at run-start; is this an invariant or an implementation choice)? [Clarity, Spec §FR-029]

### FR-030 — Task payload field list

- [x] CHK044 - Is the FR-030 `task_kind` value `callback` vs. `review` deterministically mapped from disposition (via FR-031) — i.e., is the persona allowed to choose? [Consistency, Spec §FR-030 + §FR-031]
- [x] CHK045 - Is the FR-030 `reason_code` field's "not applicable for callback tasks" rule precise (omitted vs. set to null vs. empty string)? [Clarity, Spec §FR-030]
- [x] CHK046 - Is the FR-030 `captured_email` carve-out for callback tasks (Q5 Clarification) the ONLY case in which `captured_email` appears on a task payload, or do review tasks also carry it when present? [Coverage, Spec §FR-030 + §Clarifications]
- [x] CHK047 - Is the FR-030 `created_at` distinguished from `started_at` / `ended_at` (i.e., the task's creation timestamp is distinct from the session's call window)? [Clarity, Spec §FR-030]

### FR-031 — Per-disposition write-back shape mapping

- [x] CHK048 - Does FR-031's mapping table cover all 11 dispositions in FR-013's enum exhaustively (no missing rows)? [Completeness, Spec §FR-031 + §FR-013]
- [x] CHK049 - Is FR-031's choice that `call_back_later` produces a `callback` task payload (rather than `none`) justified by a stated rationale (vs. the FR-018 exclusion list)? [Consistency, Spec §FR-031 + §FR-018]
- [x] CHK050 - Is FR-031 consistent with FR-018's exclusion set — for every excluded disposition (`not_interested`, `wrong_number`, `do_not_call`, `failed`, `blocked`), FR-031 must show `none` in the task column? [Consistency, Spec §FR-031 + §FR-018]
- [x] CHK051 - Is the FR-031 row for `needs_human_review` consistent with the persona contract's escalation flow (every escalation produces a review task)? [Consistency, Spec §FR-031 + §FR-009 + Contracts §persona.md]

### FR-032 — Per-disposition new_status mapping

- [x] CHK052 - Does FR-032's mapping table cover all 11 dispositions exhaustively? [Completeness, Spec §FR-032 + §FR-013]
- [x] CHK053 - Is FR-032's choice for `interested_callback_requested` → `new_status='ready'` consistent with FR-021's attempt-count gate (i.e., the callback attempt will be a fresh eligibility evaluation, gated by max_attempts)? [Consistency, Spec §FR-032 + §FR-021]
- [x] CHK054 - Is FR-032's choice for `wrong_number` → `new_status='blocked'` precise about whether subsequent re-attempts are allowed or permanently blocked? [Clarity, Spec §FR-032]
- [x] CHK055 - Is FR-032's row for `blocked` (`new_status` = unchanged from pre-run value) consistent with FR-029's requirement that the payload be emitted for every processed record (a no-op transition is still a payload)? [Consistency, Spec §FR-029 + §FR-032]
- [x] CHK056 - Is FR-032's `do_not_call` → `dnc` transition consistent with the DNC-mid-call Edge Case (which sets `callable_status='dnc'` directly)? [Consistency, Spec §FR-032 + §Edge Cases]
- [x] CHK057 - Is FR-032's mapping for `failed` → `new_status='ready'` justified (i.e., transport failures are retriable)? [Clarity, Spec §FR-032]
