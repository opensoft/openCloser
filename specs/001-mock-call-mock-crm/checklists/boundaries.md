# Boundaries & Architecture Requirements Quality Checklist: Slice 1 — Mock Call, Mock CRM

**Purpose**: Validate the quality, clarity, and completeness of requirements for the five module boundaries (Interaction Core, Eligibility, Mock Call Transport, Persona, Mock CRM Write-back), their contract surfaces, leak prohibitions, and forward-symmetry claims. Unit tests for the *requirements*, not for the implementation.

**Created**: 2026-05-19
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [ ] CHK001 - Are all five module boundaries (Interaction Core / Orchestrator, Eligibility, Mock Call Transport, Persona, Mock CRM Write-back) named explicitly and consistently? [Completeness, Spec §Constitution Alignment + §SC-009]
- [ ] CHK002 - Are the named contract surfaces (interfaces, method lists, payload shapes) specified for each of the five modules? [Gap, Spec §Constitution Alignment] → **RESOLVED-BY-FR-033**
- [ ] CHK003 - Is the prohibition on cross-boundary leaks (business rule, persona language, vendor-shape detail) specified with concrete examples per relevant pair of modules? [Gap, Spec §Constitution Alignment + §FR-016]
- [ ] CHK004 - Are the future-Slice substitution targets enumerated for each boundary (SignalWire → Mock Call Transport, Dataverse → Mock CRM Write-back, real persona runtime → Persona, real CRM-owned queue → local queue)? [Completeness, Spec §FR-008 + §FR-016 + §Assumptions]
- [ ] CHK005 - Is the responsibility of the Interaction Core (orchestrator) specified explicitly (which decisions it owns: session lifecycle, attempt-count increments, idempotency checks, write-back triggering)? [Gap, Spec §Constitution Alignment] → **RESOLVED-BY-FR-033 + Contracts §orchestrator.md**
- [ ] CHK006 - Are the cross-boundary inputs and outputs documented for each interface (e.g., what the Eligibility module receives, what it returns to the orchestrator)? [Gap] → **RESOLVED-BY-FR-033 + Contracts §eligibility.md / §transport.md / §persona.md / §crm-writeback.md**

## Requirement Clarity

- [ ] CHK007 - Is "the only path through which call-level events enter the Interaction Core" (FR-008) defined precisely enough to gate code review (e.g., enforcement by interface, by package boundary, by review checklist)? [Clarity, Spec §FR-008]
- [ ] CHK008 - Is "the only path through which the workflow records Phone Call-like activities, queue-status updates, and Task-like callback/review actions" (Constitution Alignment) defined precisely enough to gate code review? [Clarity, Spec §Constitution Alignment]
- [ ] CHK009 - Is "conceptual contract" — used to describe transport symmetry (FR-008) and CRM symmetry (FR-016) — defined operationally (a named interface file, a method-list document, a reviewer-judgment phrase)? [Ambiguity, Spec §FR-008 + §FR-016]
- [ ] CHK010 - Is "vendor-shape detail" (Constitution Alignment) defined with concrete examples (e.g., Dataverse-specific field names; SignalWire-specific event payload keys)? [Clarity, Spec §Constitution Alignment]

## Requirement Consistency

- [ ] CHK011 - Are the persona's responsibilities (disclosure language, allowed claims, extraction schema, disposition rules, escalation rules) consistently named between the Constitution Alignment section and FR-009 (same five items, same wording)? [Consistency, Spec §Constitution Alignment + §FR-009]
- [ ] CHK012 - Is the "no business rule in transport" requirement consistent with the transport's mandated responsibility to emit duplicate-event variants (which is itself a rule about transport behavior — is that a "business" rule or a "protocol" rule)? [Consistency, Spec §FR-006 + §Constitution Alignment]
- [ ] CHK013 - Is the "no parallel campaign workflow, UI, or follow-up surface" prohibition consistent across the Constitution Alignment and the Assumptions section's CRM-control-plane note? [Consistency, Spec §Constitution Alignment + §Assumptions]
- [ ] CHK014 - Are the five module names used consistently across Constitution Alignment, SC-009, and any related FRs (Interaction Core vs. orchestrator vs. workflow — is one canonical term chosen)? [Consistency, Spec §Constitution Alignment + §SC-009]
- [ ] CHK015 - Is the "Interaction Core" referenced consistently in FR-008 (transport feeds Core) and FR-016 (Core does not depend on mock CRM shapes)? [Consistency, Spec §FR-008 + §FR-016]

## Acceptance Criteria Quality

- [ ] CHK016 - Is SC-009 ("each module exercisable in isolation against fixtures without instantiating the others") measurable per-module with a clearly defined stub surface (i.e., is the stub-API for each boundary documented)? [Measurability, Spec §SC-009]
- [ ] CHK017 - Is SC-008 (Slice 2 reuse of CRM adapter shape) phrased as a Slice 1 deliverable check (e.g., "interface signature documented and reviewed") rather than a deferred verification? [Measurability, Spec §SC-008]
- [ ] CHK018 - Is the "no leak" prohibition between boundaries verifiable by code-review checklist or static analysis (e.g., dependency-direction rules), rather than requiring runtime verification? [Measurability, Spec §Constitution Alignment + §FR-016]

## Scenario Coverage

- [ ] CHK019 - Are requirements specified for what happens when a future module substitution (e.g., real Dataverse adapter) reveals a missing method on the conceptual contract — is the Slice 1 spec the source of truth, or is the future adapter free to add methods? [Coverage, Gap]
- [ ] CHK020 - Are requirements specified for the boundary between persona and Interaction Core when the persona needs orchestration-level information (e.g., max attempts remaining, configured call window, current attempt number)? [Coverage, Gap]
- [ ] CHK021 - Are requirements specified for the boundary between Eligibility and the local state store (does Eligibility read directly from the store, or via the orchestrator)? [Coverage, Gap]
- [ ] CHK022 - Are requirements specified for the boundary between Mock Call Transport and the Persona (does the transport feed conversation turns to the persona directly, or via the orchestrator)? [Coverage, Gap]

## Edge Case Coverage

- [ ] CHK023 - Are requirements specified for the case where the Eligibility module needs to consult the CRM adapter (e.g., a future external DNC list) — is this allowed or forbidden in Slice 1? [Edge Case, Spec §Assumptions]
- [ ] CHK024 - Are requirements specified for the case where the Transport needs to consult the Persona (or vice versa) for mid-call state — is this allowed or forbidden in Slice 1? [Edge Case, Gap]
- [ ] CHK025 - Are requirements specified for the case where the Mock CRM adapter needs to consult the Eligibility module (e.g., to decide the new queue-status value) — allowed or forbidden? [Edge Case, Gap]
- [ ] CHK026 - Are requirements specified for the case where a fixture must drive multiple modules simultaneously (a "full-system" fixture vs. per-module stubs)? [Edge Case, Gap]

## Non-Functional Requirements

- [ ] CHK027 - Are requirements specified for dependency direction (which module may depend on which) that prevent circular dependencies? [Gap, Spec §Constitution Alignment]
- [ ] CHK028 - Are requirements specified for boundary observability — when a cross-boundary call fails, which side surfaces the error? [Gap]

## Dependencies & Assumptions

- [ ] CHK029 - Is the assumption that the local queue store + mock CRM adapter jointly model the future CRM control plane explicitly stated as a Slice 1-only arrangement that will be dissolved when the real CRM arrives? [Assumption, Spec §Assumptions + §Constitution Alignment]
- [ ] CHK030 - Is the assumption that the future SignalWire transport and Dataverse adapter will satisfy the SAME conceptual contracts (not subset, not superset) documented and aligned with FR-008 / FR-016? [Assumption, Spec §FR-008 + §FR-016 + §Assumptions]
- [ ] CHK031 - Is the dependency of the Interaction Core on the Eligibility module's persisted decision (rather than re-running eligibility) acknowledged as a boundary constraint? [Assumption, Gap]

## Ambiguities & Conflicts

- [ ] CHK032 - Is the relationship between the Interaction Core (orchestrator) and the Mock CRM adapter precisely defined for queue-status writes — does the orchestrator decide the new status value, or does the adapter compute it from disposition + queue state? [Ambiguity, Spec §Constitution Alignment + §FR-015]
- [ ] CHK033 - Is the relationship between FR-006 (transport emits events) and FR-008 (transport is the only path for events into Core) — does the transport's interface include the event-emission contract, or only the event-ingestion contract? [Ambiguity, Spec §FR-006 + §FR-008]
- [ ] CHK034 - Is the boundary between the Mock Call Transport and the Persona reconciled — when a `connected` event arrives, who initiates the persona's first turn (the transport, the orchestrator, the persona itself)? [Ambiguity, Gap]
- [ ] CHK035 - Is the "five separable responsibilities" claim (Constitution Alignment) reconciled with the fact that the Interaction Core touches every other module — is the Core a sixth module, or does it own coordination as part of one of the five? [Ambiguity, Spec §Constitution Alignment]

---

## Addendum 2026-05-19 — Post-Remediation Coverage (FR-033)

The following items test the *new* FR-033 (module boundary contract surfaces) introduced during remediation.

- [ ] CHK036 - Does FR-033's "at minimum" method list cover every boundary-crossing operation the orchestrator performs? Are there orchestrator → module calls in the spec that FR-033 omits? [Completeness, Spec §FR-033]
- [ ] CHK037 - Is each method signature in FR-033 specified with input AND output types, or only the method name? [Clarity, Spec §FR-033]
- [ ] CHK038 - Is FR-033's "language-neutral interface" requirement traceable to a specific format (Pydantic class names? ABC? .pyi file?) or left to the plan? [Ambiguity, Spec §FR-033]
- [ ] CHK039 - Is the FR-033 Interaction Core's "MUST NOT contain persona language, eligibility-rule logic, transport-event interpretation, or vendor-shaped payload assembly" enforceable via the dependency-direction lint? [Measurability, Spec §FR-033 + Research §Tests]
- [ ] CHK040 - Are the FR-033 method names consistent with what each module's contract file (contracts/*.md) declares (same names, same signatures)? [Consistency, Spec §FR-033 + Contracts]
- [ ] CHK041 - Does FR-033 explicitly bind the Mock CRM adapter's three `emit_*` method names to the payload shapes in FR-028 / FR-029 / FR-030? [Consistency, Spec §FR-033 + §FR-028 / §FR-029 / §FR-030]
- [ ] CHK042 - Is FR-033's "the Slice 1 implementation is free to choose protocol details at plan time" reconciled with research.md's pick (Python ABCs, sync calls)? [Forward-compat, Spec §FR-033 + Research]
- [ ] CHK043 - Does FR-033's contract for the Persona module include `version` (FR-011) as a property of the interface, not just a runtime attribute? [Completeness, Spec §FR-011 + §FR-033]
