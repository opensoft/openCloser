# Non-Functional Requirements Checklist: Slice 2 — Mock Call, Real CRM

**Purpose**: Validate that non-functional *requirements* (performance, scalability,
reliability, observability, security posture, compliance, data governance) are either
specified measurably or explicitly and intentionally scoped out. Tests the spec, not the
implementation.
**Created**: 2026-05-22
**Re-verified**: 2026-05-22 against `plan.md`, `research.md`, `data-model.md`, `contracts/`
**Feature**: [spec.md](../spec.md)
**Depth**: Maximum (release-gate) · **Breadth**: Non-functional domain · **Audience**: PR reviewer / spec author

## Performance & Scalability

- [x] CHK001 Are performance/latency expectations for a single run specified, or explicitly declared out of scope? [Gap] — Resolved: plan §Technical Context §Performance/Scale ("not latency-critical; the only timing constraint is the bounded write-back retry budget").
- [x] CHK002 Are Dataverse API rate-limit / service-protection-limit requirements addressed or explicitly deferred? [Gap, Coverage] — Resolved: HTTP 429 is a transient error with capped `Retry-After` handling (Definitions + FR-023 + research §6).
- [x] CHK003 Is scalability explicitly declared out of scope so its absence is intentional rather than an omission? [Consistency, Spec §Assumptions] — Resolved: §Assumptions §Slice scope + §Single campaign, single item.
- [x] CHK004 Are throughput expectations (one queue item per run) stated as a deliberate constraint? [Clarity, Spec §FR-009] — Resolved: FR-009 + FR-032 + §Assumptions §Single campaign, single item.

## Reliability & Availability

- [x] CHK005 Are reliability expectations (what a "successful run" guarantees about the resulting CRM state) stated explicitly? [Clarity, Spec §SC-001] — Resolved: SC-001 + plan §Technical Context.
- [x] CHK006 Are requirements defined for the run's behavior under a partial network outage to Dataverse? [Gap, Coverage] — Resolved: Definitions §Transient Dataverse error (timeout/connection reset) + FR-023 retry + FR-002 (unreachable at start).
- [x] CHK007 Is the recovery expectation after a transient failure stated as a measurable outcome? [Measurability, Spec §FR-023] — Resolved: SC-014.
- [x] CHK008 Are requirements defined for graceful behavior when Dataverse is slow but reachable? [Gap, Coverage] — Resolved: a slow Dataverse manifests as an httpx timeout = transient error → bounded retry (Definitions + FR-023).
- [x] CHK009 Is the "no duplicate records under any retry or re-invocation" reliability guarantee stated measurably? [Measurability, Spec §SC-005] — Resolved: SC-005.

## Observability

- [x] CHK010 Are observability requirements (run logs, structured events, correlation IDs in logs) specified beyond the audit artifact? [Gap, Spec §Constitution Alignment] — Resolved: for a single-run CLI the observability surface is the operator-visible run report + exit-status contract (Definitions §Operator-visible; contracts/cli-slice2.md), the session-result artifact (FR-033), and the `crm_correlations` records (data-model §1) — all specified.
- [x] CHK011 Are the required audit data points each individually specified and traceable? [Completeness, Spec §Constitution Alignment] — Resolved: §Constitution Alignment §Auditability (MUST-list) + FR-024.
- [x] CHK012 Is the session-result artifact's required content enumerated? [Completeness, Spec §FR-033] — Resolved: FR-033 + Key Entities §Preserved Slice 1 Entities (the session result is reused unchanged from Slice 1, which enumerated its content).
- [x] CHK013 Is it specified how an operator discovers that a run needs resume vs. completed cleanly? [Gap, Clarity] — Resolved: Definitions §Operator-visible ("retry/resume state") + contracts/cli-slice2.md exit-status `resume_needed` + quickstart §7/§9.
- [x] CHK014 Are requirements defined for surfacing data-quality warnings in run output? [Clarity, Spec §FR-034] — Resolved: FR-034 (data-quality warning in the local run report and queue-status payload).

## Security Posture

- [x] CHK015 Are security requirements for secret handling complete (no leakage to logs, artifacts, or error messages)? [Completeness, Spec §FR-005] — Resolved: FR-005 + Definitions §Operator-visible.
- [x] CHK016 Is the threat assumption for Slice 2 demos (real business contacts in CRM) reflected in security requirements? [Traceability, Spec §Constitution Alignment] — Resolved: §Constitution Alignment §Safety → FR-028 (default-on redaction).
- [x] CHK017 Are failure-mode messages required to avoid leaking CRM record contents? [Completeness, Gap, Spec §FR-005] — Resolved: Definitions §Operator-visible.
- [x] CHK018 Is authentication/authorization to Dataverse addressed at the requirement level or explicitly deferred? [Gap, Spec §FR-005] — Resolved: research §2 (OAuth2 client-credentials, env-var secrets).

## Compliance & Data Governance

- [x] CHK019 Are compliance/regulatory constraints relevant to healthcare-oriented outreach identified or explicitly scoped out? [Gap, Coverage] — Resolved: §Assumptions §Compliance scope explicitly scopes Slice 2 as non-clinical/no-PHI and not a HIPAA-class patient-care or clinical workflow; clinical/PHI expansion requires separate review.
- [x] CHK020 Are data-retention requirements for transcripts and audit artifacts specified? [Gap, Coverage, Spec §FR-030] — Resolved: FR-035 and §Assumptions §Local artifact retention set a 90-day default minimum for local audit artifacts while keeping transcript retention controlled by FR-030.
- [x] CHK021 Is the no-PHI-collection posture stated as a verifiable non-functional requirement? [Gap, Spec §Constitution Alignment] — Resolved: FR-012 + FR-014 require the unchanged Slice 1 persona, which enforces the no-PHI behavior.
- [x] CHK022 Is transcript redaction positioned as a data-protection control with a stated default-on guarantee? [Completeness, Spec §FR-028] — Resolved: FR-028 + §Assumptions §Redaction default.
- [x] CHK023 Are requirements defined for safe handling and cleanup of the demo CRM record? [Gap, Spec §Assumptions] — Resolved: §Assumptions §Demo posture + quickstart §8.
- [x] CHK024 Is the absence of dedicated performance/compliance NFR sections an intentional, documented decision rather than an omission? [Clarity, Gap] — Resolved: performance remains intentionally scoped in plan §Technical Context, and §Assumptions §Compliance scope now documents the Slice 2 compliance boundary.

## Notes

- Requirements-quality audit only. Many items here are expected `[Gap]`s — the test is whether each gap is an *intentional, documented* scope decision or an unnoticed omission.
- **Re-verification result: 24/24 resolved.** The plan's Technical Context, retry/transient model, operator-visible/observability surface, compliance-scope assumption, and audit-artifact retention requirement close every item.
