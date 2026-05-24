# Constitution Alignment Checklist: Slice 2 — Mock Call, Real CRM

**Purpose**: Validate that the *requirements* faithfully and traceably encode the project
constitution (CRM control plane, thin slice, boundaries, safety, auditability). Tests the
spec's wording, not the implementation.
**Created**: 2026-05-22
**Re-verified**: 2026-05-24 against `plan.md`, `research.md`, `data-model.md`, `contracts/` (post-`45a2356` audit pass; see `reverification.md`)
**Feature**: [spec.md](../spec.md)
**Depth**: Maximum (release-gate) · **Breadth**: Constitution domain · **Audience**: PR reviewer / spec author

## CRM Control Plane

- [x] CHK001 Are requirements traceable to the constitution's CRM-first principle, with Dataverse explicitly required as the operational source of truth for queue lifecycle? [Completeness, Spec §Constitution Alignment] — Resolved: §Constitution Alignment §CRM control plane; plan §Constitution Check row I.
- [x] CHK002 Is the demotion of the local store to session/audit/artifact/correlation-only storage stated as a testable constraint? [Clarity, Spec §Constitution Alignment] — Resolved: §Constitution Alignment + §Assumptions §Source of truth.
- [x] CHK003 Does the spec require that no parallel campaign UI, custom task queue, or replacement CRM is introduced? [Completeness, Spec §Constitution Alignment] — Resolved: §Constitution Alignment + §Assumptions §Slice scope.
- [x] CHK004 Is it explicit that Dynamics remains the operator surface (no custom openCloser UI)? [Clarity, Spec §FR-033] — Resolved: FR-033 + §Constitution Alignment.

## Thin-Slice Definition

- [x] CHK005 Is the "smallest independently demonstrable outcome" expressed as a single objectively-checkable statement? [Measurability, Spec §Constitution Alignment] — Resolved: §Constitution Alignment §Thin slice.
- [x] CHK006 Is the target slice unambiguously identified as Slice 2 — Mock Call, Real CRM within the binding MVP order? [Clarity, Spec §Constitution Alignment] — Resolved: §Constitution Alignment §Thin slice.
- [x] CHK007 Does the spec state that Slice 2 isolates CRM-integration risk before real telephony? [Clarity, Spec §Constitution Alignment] — Resolved: §Constitution Alignment §Thin slice.
- [x] CHK008 Are all constitution-mandated exclusions (real telephony, live audio, real-time models, batch, scheduler, multi-worker) reflected in the Assumptions out-of-scope list? [Consistency, Spec §Assumptions] — Resolved: §Assumptions §Slice scope.

## Boundary Preservation

- [x] CHK009 Are the five preserved Slice 1 boundaries each enumerated so they can be independently verified? [Completeness, Spec §Constitution Alignment] — Resolved: plan §Project Structure + the five Slice 1 contracts (orchestrator, eligibility, transport, persona, crm-writeback).
- [x] CHK010 Is the Dataverse CRM adapter defined as a new concrete implementation behind the existing write-back interface, not a new interface? [Clarity, Spec §Constitution Alignment] — Resolved: §Constitution Alignment §Boundaries + FR-015; contracts/dataverse-adapter.md.
- [x] CHK011 Does the spec require Dataverse field names, lookups, option-set values, and owner/team IDs to be translated inside the adapter only? [Consistency, Spec §FR-016] — Resolved: FR-016.
- [x] CHK012 Is the new Dataverse queue loader required to sit behind the existing queue-item contract consumed by the eligibility evaluator? [Completeness, Spec §Constitution Alignment] — Resolved: §Boundaries + FR-008; contracts/dataverse-queue-loader.md.
- [x] CHK013 Is the new redaction boundary positioned in requirements between transcript text and artifact disk writes? [Clarity, Spec §Constitution Alignment] — Resolved: §Boundaries + FR-028; contracts/redaction-layer.md.
- [x] CHK014 Does the spec confirm the mock transport and persona are unchanged except for the FR-019 fixture pre-validation? [Consistency, Spec §FR-014] — Resolved: FR-014.

## Safety & Human Handoff (Constitution Level)

- [x] CHK015 Are the two added Slice 2 safety gates (default-on transcript redaction; owner-assigned follow-up Tasks) each backed by a discrete functional requirement? [Traceability, Spec §Constitution Alignment] — Resolved: redaction = FR-028–FR-030; owner-assigned Tasks = FR-025/FR-026.
- [x] CHK016 Is the persona safety behavior (AI-on-behalf-of-Medx disclosure, non-clinical scope, no PHI collection, immediate DNC stop, needs_human_review escalation with a reason code) carried as requirements, not only constitution prose? [Traceability, Gap] — Resolved: FR-012 + FR-014 require the Slice 1 persona unchanged, which codifies the safety behavior; FR-026/FR-027 carry the write-back side.
- [x] CHK017 Does the spec require DNC outcomes to update Dataverse DNC/opt-out fields and create no follow-up Task? [Consistency, Spec §FR-027] — Resolved: FR-027 + SC-004.
- [x] CHK018 Does the spec require callback/review Tasks to have a real, accountable assigned owner/team? [Completeness, Spec §FR-025] — Resolved: FR-025 + FR-026.

## Auditability

- [x] CHK019 Are all auditability data points (session ID, eligibility decision, mock call ID, persona version, started/ended timestamps, disposition, CRM correlation IDs) individually required? [Completeness, Spec §Constitution Alignment] — Resolved: §Constitution Alignment §Auditability (MUST-list) + FR-024.
- [x] CHK020 Does the spec require live Dataverse table and field metadata to be verified before any write? [Completeness, Spec §FR-001] — Resolved: FR-001 + FR-002.
- [x] CHK021 Is the requirement to preserve existing high-confidence CRM values outside the approved update set stated testably? [Clarity, Spec §FR-003] — Resolved: FR-003 + Definitions §High-confidence Dataverse value.
- [x] CHK022 Does the spec require duplicate provider events, repeated CLI invocations, and write-back retries to not create duplicate records? [Consistency, Spec §FR-021] — Resolved: FR-021 + SC-005.
- [x] CHK023 Is each constitution principle (CRM control plane, thin slice, boundaries, safety, auditability) traceable to at least one FR or SC? [Traceability, Spec §Requirements] — Resolved: plan §Constitution Check table maps every principle to FRs/SCs.

## Notes

- Requirements-quality audit only — every item asks whether the spec *says* the right thing, not whether code behaves.
- **Re-verification result: 23/23 resolved.** The spec's Constitution Alignment section plus the plan's Constitution Check close every item — no open constitution-domain defects.
