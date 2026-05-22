# Security & Privacy Checklist: Slice 2 — Mock Call, Real CRM

**Purpose**: Validate the *requirements* for secret handling, transcript redaction, PHI /
privacy posture, persona safety, and human-handoff Task ownership — for completeness,
clarity, consistency, and coverage. Tests the spec, not the implementation.
**Created**: 2026-05-22
**Feature**: [spec.md](../spec.md)
**Depth**: Maximum (release-gate) · **Breadth**: Security & privacy domain · **Audience**: PR reviewer / spec author

## Secret Handling

- [ ] CHK001 Are security requirements for secret handling complete (no secrets in logs, exported artifacts, or error messages)? [Completeness, Spec §FR-005]
- [ ] CHK002 Are failure-mode messages required to avoid leaking CRM record contents or secrets? [Completeness, Gap, Spec §FR-005]
- [ ] CHK003 Is the secret storage mechanism (environment variables or a secret manager) specified as a requirement? [Clarity, Spec §FR-005]

## Transcript Redaction

- [ ] CHK004 Are the default redaction patterns ("configured sensitive patterns") defined, or required to be defined, somewhere authoritative? [Gap, Spec §FR-028]
- [ ] CHK005 Is the redaction ordering ("before any transcript artifact is written to disk") stated unambiguously? [Clarity, Spec §FR-028]
- [ ] CHK006 Is the default policy ([REDACTED] replacement) specified as default-on for Slice 2? [Completeness, Spec §FR-028]
- [ ] CHK007 Is summary-only retention specified with its exact config trigger and the resulting artifact set? [Completeness, Spec §FR-030]
- [ ] CHK008 Does the spec require that no full transcript file is written under summary-only retention, while the session-result artifact still includes the summary and the retention mode? [Completeness, Spec §FR-030]
- [ ] CHK009 Is the no-op redaction policy's effect on the artifact contract specified precisely? [Completeness, Spec §FR-029]
- [ ] CHK010 Does the spec require that redaction cannot be silently disabled, and is "silently" defined? [Clarity, Spec §Assumptions]
- [ ] CHK011 Does the redaction layer preserve the normalized summary and transcript-pointer artifact contract from Slice 1? [Consistency, Spec §FR-029]
- [ ] CHK012 Are requirements defined for a malformed redaction policy or a redaction-pattern processing failure? [Coverage, Gap, Spec §FR-028]
- [ ] CHK013 Is the redaction policy's configurability scope (which patterns, which modes) bounded and specified? [Clarity, Spec §FR-028]
- [ ] CHK014 Can "transcript artifacts contain [REDACTED] in place of every matching value" be objectively verified? [Measurability, Spec §SC-009]

## PHI & Privacy Posture

- [ ] CHK015 Is the no-PHI-collection posture stated as a verifiable requirement, not only constitution prose? [Gap, Spec §Constitution Alignment]
- [ ] CHK016 Are data-retention requirements for transcripts and audit artifacts specified? [Gap, Coverage, Spec §FR-030]
- [ ] CHK017 Are compliance/regulatory constraints for healthcare-oriented outreach identified or explicitly scoped out? [Gap, Coverage]
- [ ] CHK018 Is the rationale for default-on redaction (real business contacts in CRM demos) reflected in a requirement, not only motivation text? [Traceability, Spec §Constitution Alignment]

## Persona Safety

- [ ] CHK019 Is the AI-on-behalf-of-Medx disclosure carried as a requirement? [Traceability, Gap]
- [ ] CHK020 Is the immediate DNC-stop behavior specified as a requirement with a testable trigger? [Clarity, Spec §FR-027]
- [ ] CHK021 Is the non-clinical scope boundary of the persona stated testably? [Clarity, Gap]
- [ ] CHK022 Is `needs_human_review` escalation required to carry a reason code, and is the reason-code source/enumeration defined? [Clarity, Spec §FR-026]

## Human Handoff & Task Ownership

- [ ] CHK023 Are callback/review Task ownership requirements defined for every Task-producing disposition? [Completeness, Spec §FR-025]
- [ ] CHK024 Is the default-owner-per-task-kind mapping required, with an optional approved per-item override? [Completeness, Spec §FR-025]
- [ ] CHK025 Is "approved owner override" defined with the criteria that make an override "approved"? [Ambiguity, Spec §FR-025]
- [ ] CHK026 Is the review Task required to be assigned to the configured review owner/team and to carry the human-review reason code? [Completeness, Spec §FR-026]
- [ ] CHK027 Does the spec require DNC/opt-out outcomes to create no callback or review Task, consistently across FR-027, US1, and SC-004? [Consistency, Spec §FR-027]
- [ ] CHK028 Are requirements defined for a DNC outcome where the Dataverse DNC/opt-out field cannot be located? [Coverage, Gap, Spec §FR-027]
- [ ] CHK029 Are requirements defined for a configured owner/team that no longer exists in Dataverse? [Gap, Coverage]
- [ ] CHK030 Is the `preferred_callback_window` phrase required to be preserved as free-form text in the Task, with empty/unparseable handling defined? [Coverage, Spec §Edge Cases]
- [ ] CHK031 Can "exactly one callback/review Task assigned to the configured owner" be objectively verified? [Measurability, Spec §SC-003]

## Notes

- Requirements-quality audit only.
- High-signal defects: CHK004 (default redaction patterns undefined), CHK012 (malformed-policy handling), CHK015/CHK017 (PHI & compliance posture not requirement-level), CHK025 ("approved override" undefined).
