# Non-Functional Requirements Checklist: Slice 2 — Mock Call, Real CRM

**Purpose**: Validate that non-functional *requirements* (performance, scalability,
reliability, observability, security posture, compliance, data governance) are either
specified measurably or explicitly and intentionally scoped out. Tests the spec, not the
implementation.
**Created**: 2026-05-22
**Feature**: [spec.md](../spec.md)
**Depth**: Maximum (release-gate) · **Breadth**: Non-functional domain · **Audience**: PR reviewer / spec author

## Performance & Scalability

- [ ] CHK001 Are performance/latency expectations for a single run specified, or explicitly declared out of scope? [Gap]
- [ ] CHK002 Are Dataverse API rate-limit / service-protection-limit requirements addressed or explicitly deferred? [Gap, Coverage]
- [ ] CHK003 Is scalability explicitly declared out of scope so its absence is intentional rather than an omission? [Consistency, Spec §Assumptions]
- [ ] CHK004 Are throughput expectations (one queue item per run) stated as a deliberate constraint? [Clarity, Spec §FR-009]

## Reliability & Availability

- [ ] CHK005 Are reliability expectations (what a "successful run" guarantees about the resulting CRM state) stated explicitly? [Clarity, Spec §SC-001]
- [ ] CHK006 Are requirements defined for the run's behavior under a partial network outage to Dataverse? [Gap, Coverage]
- [ ] CHK007 Is the recovery expectation after a transient failure stated as a measurable outcome? [Measurability, Spec §FR-023]
- [ ] CHK008 Are requirements defined for graceful behavior when Dataverse is slow but reachable? [Gap, Coverage]
- [ ] CHK009 Is the "no duplicate records under any retry or re-invocation" reliability guarantee stated measurably? [Measurability, Spec §SC-005]

## Observability

- [ ] CHK010 Are observability requirements (run logs, structured events, correlation IDs in logs) specified beyond the audit artifact? [Gap, Spec §Constitution Alignment]
- [ ] CHK011 Are the required audit data points each individually specified and traceable? [Completeness, Spec §Constitution Alignment]
- [ ] CHK012 Is the session-result artifact's required content enumerated? [Completeness, Spec §FR-033]
- [ ] CHK013 Is it specified how an operator discovers that a run needs resume vs. completed cleanly? [Gap, Clarity]
- [ ] CHK014 Are requirements defined for surfacing data-quality warnings in run output? [Clarity, Spec §FR-034]

## Security Posture

- [ ] CHK015 Are security requirements for secret handling complete (no leakage to logs, artifacts, or error messages)? [Completeness, Spec §FR-005]
- [ ] CHK016 Is the threat assumption for Slice 2 demos (real business contacts in CRM) reflected in security requirements? [Traceability, Spec §Constitution Alignment]
- [ ] CHK017 Are failure-mode messages required to avoid leaking CRM record contents? [Completeness, Gap, Spec §FR-005]
- [ ] CHK018 Is authentication/authorization to Dataverse addressed at the requirement level or explicitly deferred? [Gap, Spec §FR-005]

## Compliance & Data Governance

- [ ] CHK019 Are compliance/regulatory constraints relevant to healthcare-oriented outreach identified or explicitly scoped out? [Gap, Coverage]
- [ ] CHK020 Are data-retention requirements for transcripts and audit artifacts specified? [Gap, Coverage, Spec §FR-030]
- [ ] CHK021 Is the no-PHI-collection posture stated as a verifiable non-functional requirement? [Gap, Spec §Constitution Alignment]
- [ ] CHK022 Is transcript redaction positioned as a data-protection control with a stated default-on guarantee? [Completeness, Spec §FR-028]
- [ ] CHK023 Are requirements defined for safe handling and cleanup of the demo CRM record? [Gap, Spec §Assumptions]
- [ ] CHK024 Is the absence of dedicated performance/compliance NFR sections an intentional, documented decision rather than an omission? [Clarity, Gap]

## Notes

- Requirements-quality audit only. Many items here are expected `[Gap]`s — the test is whether each gap is an *intentional, documented* scope decision or an unnoticed omission.
- High-signal defects: CHK002 (rate limits), CHK006/CHK008 (network/slow-Dataverse behavior), CHK010 (observability beyond audit artifact), CHK019/CHK021 (compliance & PHI posture).
