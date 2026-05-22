# Constitution Alignment Checklist: Slice 2 — Mock Call, Real CRM

**Purpose**: Validate that the *requirements* faithfully and traceably encode the project
constitution (CRM control plane, thin slice, boundaries, safety, auditability). Tests the
spec's wording, not the implementation.
**Created**: 2026-05-22
**Feature**: [spec.md](../spec.md)
**Depth**: Maximum (release-gate) · **Breadth**: Constitution domain · **Audience**: PR reviewer / spec author

## CRM Control Plane

- [ ] CHK001 Are requirements traceable to the constitution's CRM-first principle, with Dataverse explicitly required as the operational source of truth for queue lifecycle? [Completeness, Spec §Constitution Alignment]
- [ ] CHK002 Is the demotion of the local store to session/audit/artifact/correlation-only storage stated as a testable constraint? [Clarity, Spec §Constitution Alignment]
- [ ] CHK003 Does the spec require that no parallel campaign UI, custom task queue, or replacement CRM is introduced? [Completeness, Spec §Constitution Alignment]
- [ ] CHK004 Is it explicit that Dynamics remains the operator surface (no custom openCloser UI)? [Clarity, Spec §FR-033]

## Thin-Slice Definition

- [ ] CHK005 Is the "smallest independently demonstrable outcome" expressed as a single objectively-checkable statement? [Measurability, Spec §Constitution Alignment]
- [ ] CHK006 Is the target slice unambiguously identified as Slice 2 — Mock Call, Real CRM within the binding MVP order? [Clarity, Spec §Constitution Alignment]
- [ ] CHK007 Does the spec state that Slice 2 isolates CRM-integration risk before real telephony? [Clarity, Spec §Constitution Alignment]
- [ ] CHK008 Are all constitution-mandated exclusions (real telephony, live audio, real-time models, batch, scheduler, multi-worker) reflected in the Assumptions out-of-scope list? [Consistency, Spec §Assumptions]

## Boundary Preservation

- [ ] CHK009 Are the five preserved Slice 1 boundaries each enumerated so they can be independently verified? [Completeness, Spec §Constitution Alignment]
- [ ] CHK010 Is the Dataverse CRM adapter defined as a new concrete implementation behind the existing write-back interface, not a new interface? [Clarity, Spec §Constitution Alignment]
- [ ] CHK011 Does the spec require Dataverse field names, lookups, option-set values, and owner/team IDs to be translated inside the adapter only? [Consistency, Spec §FR-016]
- [ ] CHK012 Is the new Dataverse queue loader required to sit behind the existing queue-item contract consumed by the eligibility evaluator? [Completeness, Spec §Constitution Alignment]
- [ ] CHK013 Is the new redaction boundary positioned in requirements between transcript text and artifact disk writes? [Clarity, Spec §Constitution Alignment]
- [ ] CHK014 Does the spec confirm the mock transport and persona are unchanged except for the FR-019 fixture pre-validation? [Consistency, Spec §FR-014]

## Safety & Human Handoff (Constitution Level)

- [ ] CHK015 Are the two added Slice 2 safety gates (default-on transcript redaction; owner-assigned follow-up Tasks) each backed by a discrete functional requirement? [Traceability, Spec §Constitution Alignment]
- [ ] CHK016 Is the persona safety behavior (AI-on-behalf-of-Medx disclosure, non-clinical scope, no PHI collection, immediate DNC stop, needs_human_review escalation with a reason code) carried as requirements, not only constitution prose? [Traceability, Gap]
- [ ] CHK017 Does the spec require DNC outcomes to update Dataverse DNC/opt-out fields and create no follow-up Task? [Consistency, Spec §FR-027]
- [ ] CHK018 Does the spec require callback/review Tasks to have a real, accountable assigned owner/team? [Completeness, Spec §FR-025]

## Auditability

- [ ] CHK019 Are all auditability data points (session ID, eligibility decision, mock call ID, persona version, started/ended timestamps, disposition, CRM correlation IDs) individually required? [Completeness, Spec §Constitution Alignment]
- [ ] CHK020 Does the spec require live Dataverse table and field metadata to be verified before any write? [Completeness, Spec §FR-001]
- [ ] CHK021 Is the requirement to preserve existing high-confidence CRM values outside the approved update set stated testably? [Clarity, Spec §FR-003]
- [ ] CHK022 Does the spec require duplicate provider events, repeated CLI invocations, and write-back retries to not create duplicate records? [Consistency, Spec §FR-021]
- [ ] CHK023 Is each constitution principle (CRM control plane, thin slice, boundaries, safety, auditability) traceable to at least one FR or SC? [Traceability, Spec §Requirements]

## Notes

- Requirements-quality audit only — every item asks whether the spec *says* the right thing, not whether code behaves.
- `[Gap]` marks a constitution expectation not yet pinned to a discrete requirement.
