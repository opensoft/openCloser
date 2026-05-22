# Run Modes, CLI & Configuration Checklist: Slice 2 — Mock Call, Real CRM

**Purpose**: Validate the *requirements* for dry-run / write-enabled modes, the CLI surface,
configuration, secrets loading, readiness validation, and demo evidence — for completeness,
clarity, consistency, and coverage. Tests the spec, not the implementation.
**Created**: 2026-05-22
**Feature**: [spec.md](../spec.md)
**Depth**: Maximum (release-gate) · **Breadth**: Run modes & configuration domain · **Audience**: PR reviewer / spec author

## Run Modes & Default

- [ ] CHK001 Is the CLI default run mode (dry-run) stated as a requirement and consistent across all spec sections? [Consistency, Spec §FR-031]
- [ ] CHK002 Is the explicit flag that enables write-enabled mode named, or at least required to be unambiguous? [Clarity, Spec §FR-031]
- [ ] CHK003 Does the spec require dry-run to validate the mapping and produce planned write-back artifacts with zero CRM creates/updates? [Completeness, Spec §FR-031]
- [ ] CHK004 Are "planned write-back artifacts" defined with enough structure to verify dry-run / write-enabled payload parity? [Clarity, Spec §FR-031]
- [ ] CHK005 Can "the same payload content" in dry-run vs. write-enabled be objectively compared? [Measurability, Spec §US2]
- [ ] CHK006 Is it specified that dry-run still surfaces mapping gaps (does not silently pass)? [Completeness, Spec §US2]
- [ ] CHK007 Is it specified that dry-run does not require write credentials, and that their absence is not a dry-run error? [Completeness, Spec §Edge Cases]
- [ ] CHK008 Are requirements defined for an explicit write-enabled run when write credentials are missing? [Coverage, Spec §FR-007]

## CLI Surface

- [ ] CHK009 Is "one CLI invocation processes exactly one queue item" stated precisely? [Clarity, Spec §FR-032]
- [ ] CHK010 Are the CLI's required inputs (campaign, queue-item selector, fixture, run mode) enumerated? [Completeness, Gap, Spec §FR-032]
- [ ] CHK011 Is the CLI's exit-status contract (success / blocked / failed / resume-needed) defined? [Gap, Clarity]
- [x] CHK012 Is "operator-visible error/message" defined with a concrete surfacing channel (stderr, exit code, report file)? [Ambiguity, Spec §FR-007] — Resolved by Definitions.

## Configuration

- [ ] CHK013 Are all non-secret mapping-configuration keys (queue fields, status values, task owner mapping, run mode) enumerated? [Completeness, Spec §FR-006]
- [ ] CHK014 Are requirements defined for invalid configuration (e.g., a status value that is not a valid option-set member)? [Coverage, Gap, Spec §FR-007]
- [ ] CHK015 Is "callable status" defined as a configurable value with a single source of truth? [Clarity, Spec §FR-011]
- [ ] CHK016 Does the spec separate non-secret config (file) from secrets (env vars / secret manager) unambiguously? [Clarity, Spec §FR-005]
- [ ] CHK017 Are configuration precedence rules (defaults vs. per-queue-item overrides) specified? [Clarity, Spec §FR-025]

## Secrets Loading

- [ ] CHK018 Are all required Dataverse connection secrets enumerated so startup validation can check each one? [Completeness, Spec §FR-005]
- [ ] CHK019 Is the Dataverse authentication method either specified or explicitly and intentionally deferred to planning? [Gap, Spec §FR-005]
- [ ] CHK020 Does the spec require secrets to never be written to logs or exported artifacts? [Completeness, Spec §FR-005]
- [ ] CHK021 Are requirements defined for secret values being absent vs. present-but-invalid (distinct failure messages)? [Coverage, Spec §FR-007]

## Readiness & Demo Evidence

- [ ] CHK022 Does the spec require startup/readiness validation to fail with a clear, operator-visible message when mappings or credentials are missing? [Completeness, Spec §FR-007]
- [ ] CHK023 Does readiness validation behave consistently across dry-run and write-enabled modes (minus credential checks)? [Consistency, Spec §FR-007]
- [ ] CHK024 Is US3 ("Slice 2 setup") reconciled with FR-007 ("startup/readiness validation") — same gate or two distinct steps? [Ambiguity, Spec §US3]
- [ ] CHK025 Are the required end-of-run demo artifacts (updated queue item, Phone Call activity, Task, session result, transcript pointer) each individually specified? [Completeness, Spec §FR-033]
- [ ] CHK026 Is "repeatable demo path" defined with criteria that make repeatability checkable? [Measurability, Spec §FR-033]
- [ ] CHK027 Does the spec require the demo outcome to be inspectable without a custom openCloser UI? [Completeness, Spec §FR-033]
- [ ] CHK028 Is the documented manual cleanup/rollback for the demo CRM record specified? [Gap, Spec §Assumptions]

## Notes

- Requirements-quality audit only.
- Resolved in this pass: CHK012 ("operator-visible" defined).
- Remaining high-signal defects: CHK004 (planned-artifact structure), CHK010/CHK011 (CLI inputs and exit-status contract), CHK019 (auth method), CHK024 (setup vs. readiness ambiguity).
