# openCloser Constitution

**Status**: Active
**Created**: 2026-05-19
**Source**: Authored from Slice 1 spec.md `## Constitution Alignment` (`specs/001-mock-call-mock-crm/spec.md`)
**Scope**: Binding for every feature in the openCloser repository, present and future.

openCloser is a CRM-first AI communication platform for healthcare-oriented outreach. This document codifies the project's non-negotiable principles. Each principle binds spec authorship, planning, implementation, and review. Conflicts between these principles and a feature's spec/plan/tasks/code are automatically CRITICAL findings during `/speckit.analyze` and MUST be resolved by adjusting the feature artifacts — not by diluting or reinterpreting a principle here. Principles may be amended only via an explicit, repository-wide update outside any individual feature's workflow.

---

## Principle 1 — CRM as the conceptual control plane

The CRM is the conceptual control plane for the entire product, regardless of which slice is being built. Every workflow MUST record Phone Call-like activities, queue-status updates, and Task-like callback/review actions through the CRM write-back adapter. There MUST NOT be a parallel campaign workflow, parallel UI, or parallel follow-up surface that bypasses or duplicates the CRM contract.

In early slices the CRM write-back may be a mock adapter; in later slices it MUST be the real Dataverse (Dynamics) adapter. The mock and the real adapter MUST satisfy the same conceptual contract — the same operations, the same payload shapes — so that swapping in the real CRM is a name-only change rather than a shape change.

If a slice cannot include the real CRM yet, the local queue store + mock CRM adapter jointly stand in for the CRM control plane. That arrangement is always Slice-bounded and explicit; it MUST NOT evolve into a parallel surface.

## Principle 2 — Thin, sequenced slices

Work is sequenced as a binding MVP slice order. Each slice has the smallest independently demonstrable outcome, and slices MUST NOT be skipped, reordered, or merged without an explicit constitution amendment.

The current binding sequence (recorded for traceability; amend here when slices land):

1. **Slice 1 — Mock Call, Mock CRM** — first end-to-end product loop on one queue record, fixture-driven, no SignalWire / no Dataverse / no UI.
2. **Slice 2 — Real CRM** — swap the mock CRM adapter for the Dataverse adapter against the same contract.
3. **Slice 3 — Real Telephony** — swap the mock transport for the SignalWire transport against the same contract. Live LLM-driven persona may appear here or be deferred.
4. **Subsequent slices** — additional personas (clinical with appropriate safeguards), multi-record / batch processing, admin UI, multi-worker scaling, etc.

Each slice's spec MUST name the target slice, MUST list what's deferred, and MUST keep deferred capabilities out of scope.

## Principle 3 — Five separable boundaries

Every feature touching the call loop MUST keep these five responsibilities distinct, even when a slice mocks several of them:

1. **Interaction Core / orchestrator** — owns session lifecycle, idempotency, attempt-count, the sequence of calls into the other four modules.
2. **Eligibility evaluator** — owns the eligibility rules and produces a persisted decision.
3. **Call transport** — owns call-attempt initiation, provider-event emission, and provider-call-ID assignment.
4. **Persona module** — owns the conversation. Specifically owns: disclosure language, allowed claims, extraction schema, disposition rules, escalation rules, and persona version.
5. **CRM write-back adapter** — owns payload assembly and emission for Phone Call-like activities, queue-status updates, and Task-like actions.

No business rule, no persona language, no vendor-shape detail (Dataverse field names, SignalWire event keys) may leak across these boundaries. The call transport interface and the CRM adapter interface MUST present the same conceptual contract whether mock or real. Each module MUST be exercisable in isolation against stubs.

## Principle 4 — Safety and human handoff are first-class invariants

Every connected conversation MUST:

- Disclose, in the persona's first utterance after `connected`, that the caller is an AI assistant calling on behalf of Medx.
- Remain non-clinical. The persona MUST NOT collect resident or patient health information.
- Honor DNC / opt-out statements before any further sales utterance. Mid-call DNC MUST persist the signal: the queue record's `dnc_flag` and `callable_status='dnc'` MUST be set in local state, and the CRM queue-status update MUST reflect the transition.
- Respect a configured local call window and a configured maximum-attempts limit before placing any call.
- Mark uncertain or unsafe outcomes for human review with a stated reason drawn from an enumerated reason-code set. Free-form reasons are forbidden.

Interested or uncertain outcomes MUST produce a callback or review task payload through the CRM write-back. Excluded dispositions (`not_interested`, `wrong_number`, `do_not_call`, `failed`, `blocked`) MUST NOT produce a follow-up task — this exclusion is binding regardless of persona disposition rules.

## Principle 5 — Auditability and idempotency

Every processed queue item MUST produce a traceable session record carrying, at minimum: session ID, queue-item ID, mock or real provider call ID when a call was placed, persona version, started / ended timestamps in ISO 8601 / UTC / millisecond precision, final disposition, transcript or transcript pointer, and the inputs and outputs of the eligibility decision.

Every provider event MUST carry a stable identity. The system MUST treat provider-style events idempotently: duplicate events MUST be no-ops with respect to session state, normalized result, attempt count, all write-back payloads, and exported artifacts. Conflicting late events MUST NOT mutate a finalized disposition; they MUST be recorded for audit in a separate channel.

Attempt-count increments MUST be tied to a unique call attempt and MUST occur exactly once per provider call ID.

Exported artifacts MUST be readable, MUST minimize sensitive data, MUST NOT contain secrets, and MUST be deterministic across reruns of the same fixture so audit and idempotency invariants are testable by direct comparison.

---

## Governance

- Amendments to this constitution require an explicit, repository-wide decision, recorded as a commit to this file with a Rationale section.
- A feature's spec.md MUST include a `## Constitution Alignment` section that maps the feature's behavior onto these five principles.
- A feature's plan.md MUST include a `## Constitution Check` that evaluates the plan against each principle.
- A feature's `/speckit.analyze` step MUST flag any principle violation as CRITICAL and refuse to recommend `/speckit.implement` until resolved.

## Traceability

- **Principle 1** maps to spec.md `## Constitution Alignment → CRM control plane` and to FR-015 / FR-016 / FR-029 of any feature that touches write-backs.
- **Principle 2** maps to each feature's `## Assumptions → Slice scope` section.
- **Principle 3** maps to spec.md `## Constitution Alignment → Boundaries`, to FR-008 + FR-016 + FR-033, and to SC-009.
- **Principle 4** maps to spec.md `## Constitution Alignment → Safety and human handoff`, to FR-010 + FR-018 + FR-035 + FR-036, and to the DNC-mid-call edge case.
- **Principle 5** maps to spec.md `## Constitution Alignment → Auditability`, to FR-019 + FR-020 + FR-021, and to SC-005 + SC-006.
