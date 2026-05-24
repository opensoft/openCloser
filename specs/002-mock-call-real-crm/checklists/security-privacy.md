# Security & Privacy Checklist: Slice 2 — Mock Call, Real CRM

**Purpose**: Validate the *requirements* for secret handling, transcript redaction, PHI /
privacy posture, persona safety, and human-handoff Task ownership — for completeness,
clarity, consistency, and coverage. Tests the spec, not the implementation.
**Created**: 2026-05-22
**Re-verified**: 2026-05-24 against `plan.md`, `research.md`, `data-model.md`, `contracts/` (post-`45a2356` audit pass; see `reverification.md`)
**Feature**: [spec.md](../spec.md)
**Depth**: Maximum (release-gate) · **Breadth**: Security & privacy domain · **Audience**: PR reviewer / spec author

## Secret Handling

- [x] CHK001 Are security requirements for secret handling complete (no secrets in logs, exported artifacts, or error messages)? [Completeness, Spec §FR-005] — Resolved: FR-005 + Definitions §Operator-visible.
- [x] CHK002 Are failure-mode messages required to avoid leaking CRM record contents or secrets? [Completeness, Gap, Spec §FR-005] — Resolved: Definitions §Operator-visible ("without logging secrets or full CRM record contents").
- [x] CHK003 Is the secret storage mechanism (environment variables or a secret manager) specified as a requirement? [Clarity, Spec §FR-005] — Resolved: FR-005 + research §2.

## Transcript Redaction

- [x] CHK004 Are the default redaction patterns ("configured sensitive patterns") defined, or required to be defined, somewhere authoritative? [Gap, Spec §FR-028] — Resolved: data-model §3 + research §8 (default `[redaction] patterns` in `slice2.toml` — phone-number and email regexes).
- [x] CHK005 Is the redaction ordering ("before any transcript artifact is written to disk") stated unambiguously? [Clarity, Spec §FR-028] — Resolved: FR-028 + contracts/redaction-layer.md.
- [x] CHK006 Is the default policy ([REDACTED] replacement) specified as default-on for Slice 2? [Completeness, Spec §FR-028] — Resolved: FR-028 + §Assumptions §Redaction default + contracts/redaction-layer.md.
- [x] CHK007 Is summary-only retention specified with its exact config trigger and the resulting artifact set? [Completeness, Spec §FR-030] — Resolved: FR-030 + data-model §3 (`retention = "summary-only"`) + contracts/redaction-layer.md.
- [x] CHK008 Does the spec require that no full transcript file is written under summary-only retention, while the session-result artifact still includes the summary and the retention mode? [Completeness, Spec §FR-030] — Resolved: FR-030.
- [x] CHK009 Is the no-op redaction policy's effect on the artifact contract specified precisely? [Completeness, Spec §FR-029] — Resolved: FR-029 + contracts/redaction-layer.md.
- [x] CHK010 Does the spec require that redaction cannot be silently disabled, and is "silently" defined? [Clarity, Spec §Assumptions] — Resolved: §Assumptions + contracts/redaction-layer.md (turning it off requires an explicit `policy = "noop"`).
- [x] CHK011 Does the redaction layer preserve the normalized summary and transcript-pointer artifact contract from Slice 1? [Consistency, Spec §FR-029] — Resolved: FR-029 + contracts/redaction-layer.md.
- [x] CHK012 Are requirements defined for a malformed redaction policy or a redaction-pattern processing failure? [Coverage, Gap, Spec §FR-028] — Resolved: §Edge Cases and FR-007 require malformed redaction policy configuration to fail startup/readiness validation before transcript writing, session creation, claim, attempt increment, or CRM write.
- [x] CHK013 Is the redaction policy's configurability scope (which patterns, which modes) bounded and specified? [Clarity, Spec §FR-028] — Resolved: FR-028 + data-model §3 (`policy`, `retention`, `patterns`) + contracts/redaction-layer.md.
- [x] CHK014 Can "transcript artifacts contain [REDACTED] in place of every matching value" be objectively verified? [Measurability, Spec §SC-009] — Resolved: SC-009.

## PHI & Privacy Posture

- [x] CHK015 Is the no-PHI-collection posture stated as a verifiable requirement, not only constitution prose? [Gap, Spec §Constitution Alignment] — Resolved: FR-012 + FR-014 require the Slice 1 persona unchanged, which enforces the non-clinical / no-PHI behavior.
- [x] CHK016 Are data-retention requirements for transcripts and audit artifacts specified? [Gap, Coverage, Spec §FR-030] — Resolved: FR-035 and §Assumptions §Local artifact retention set a 90-day default minimum for local audit artifacts while keeping transcript retention controlled by FR-030.
- [x] CHK017 Are compliance/regulatory constraints for healthcare-oriented outreach identified or explicitly scoped out? [Gap, Coverage] — Resolved: §Assumptions §Compliance scope explicitly scopes Slice 2 as non-clinical/no-PHI and not a HIPAA-class patient-care or clinical workflow; clinical/PHI expansion requires separate review.
- [x] CHK018 Is the rationale for default-on redaction (real business contacts in CRM demos) reflected in a requirement, not only motivation text? [Traceability, Spec §Constitution Alignment] — Resolved: FR-028 (the requirement) + §Constitution Alignment §Safety (the rationale).

## Persona Safety

- [x] CHK019 Is the AI-on-behalf-of-Medx disclosure carried as a requirement? [Traceability, Gap] — Resolved: FR-012 + FR-014 require the unchanged Slice 1 persona, which carries the disclosure.
- [x] CHK020 Is the immediate DNC-stop behavior specified as a requirement with a testable trigger? [Clarity, Spec §FR-027] — Resolved: FR-027 (DNC / mid-call opt-out) + FR-012/FR-014 (persona stop behavior).
- [x] CHK021 Is the non-clinical scope boundary of the persona stated testably? [Clarity, Gap] — Resolved: FR-012 + FR-014 (Slice 1 persona reused unchanged).
- [x] CHK022 Is `needs_human_review` escalation required to carry a reason code, and is the reason-code source/enumeration defined? [Clarity, Spec §FR-026] — Resolved: FR-026 + specs/001/contracts/crm-writeback.md (`reason_code: HumanReviewReason` enumeration reused).

## Human Handoff & Task Ownership

- [x] CHK023 Are callback/review Task ownership requirements defined for every Task-producing disposition? [Completeness, Spec §FR-025] — Resolved: FR-025 + FR-026 + crm-writeback.md per-disposition emission map.
- [x] CHK024 Is the default-owner-per-task-kind mapping required, with an optional approved per-item override? [Completeness, Spec §FR-025] — Resolved: FR-025 + data-model §3 (`[task_owners]`).
- [x] CHK025 Is "approved owner override" defined with the criteria that make an override "approved"? [Ambiguity, Spec §FR-025] — Resolved: Definitions §Approved owner override and FR-025 require a mapped override source, active enabled Dataverse user/team resolution, permitted Task kind, fallback warning, and no unverified owner/team write.
- [x] CHK026 Is the review Task required to be assigned to the configured review owner/team and to carry the human-review reason code? [Completeness, Spec §FR-026] — Resolved: FR-026.
- [x] CHK027 Does the spec require DNC/opt-out outcomes to create no callback or review Task, consistently across FR-027, US1, and SC-004? [Consistency, Spec §FR-027] — Resolved: FR-027 + US1 scenario 4 + SC-004.
- [x] CHK028 Are requirements defined for a DNC outcome where the Dataverse DNC/opt-out field cannot be located? [Coverage, Gap, Spec §FR-027] — Resolved: the DNC/opt-out field is required metadata; its absence blocks write-enabled processing (FR-002 + FR-001).
- [x] CHK029 Are requirements defined for a configured owner/team that no longer exists in Dataverse? [Gap, Coverage] — Resolved: owner/team is verified metadata (Definitions §Lightweight live verification); a 404 is a Permanent error (FR-002).
- [x] CHK030 Is the `preferred_callback_window` phrase required to be preserved as free-form text in the Task, with empty/unparseable handling defined? [Coverage, Spec §Edge Cases] — Resolved: §Edge Cases + §Assumptions (preserved verbatim as free-form text; no parsing, so an unparseable phrase is moot).
- [x] CHK031 Can "exactly one callback/review Task assigned to the configured owner" be objectively verified? [Measurability, Spec §SC-003] — Resolved: SC-003.

## No-Secrets-in-Artifacts Negative Assertion (T047 — added 2026-05-24)

- [x] CHK032 Does FR-005's "no secrets in logs/artifacts" requirement extend to a verifiable negative-assertion test (T047) over every produced local audit artifact — run report, planned/actual write-back payloads, redacted transcript file, `crm_correlations` and `writeback_progress` rows — covering the four env-var secrets (`DATAVERSE_TENANT_ID` / `CLIENT_ID` / `CLIENT_SECRET` / `ENV_URL`) via literal-substring match? [Coverage, Spec §FR-005, §FR-035, T047] — Resolved: T047 task description enumerates inspection surface, secret set, and match style; FR-035's "secrets MUST NOT be retained" reinforces.

## Notes

- Requirements-quality audit only.
- **Re-verification result: 31/31 resolved.** Malformed redaction-policy handling, audit-artifact retention, compliance scope, and approved-owner-override criteria are now specified; every item is closed.
