# Run Modes, CLI & Configuration Checklist: Slice 2 — Mock Call, Real CRM

**Purpose**: Validate the *requirements* for dry-run / write-enabled modes, the CLI surface,
configuration, secrets loading, readiness validation, and demo evidence — for completeness,
clarity, consistency, and coverage. Tests the spec, not the implementation.
**Created**: 2026-05-22
**Re-verified**: 2026-05-22 against `plan.md`, `research.md`, `data-model.md`, `contracts/`
**Feature**: [spec.md](../spec.md)
**Depth**: Maximum (release-gate) · **Breadth**: Run modes & configuration domain · **Audience**: PR reviewer / spec author

## Run Modes & Default

- [x] CHK001 Is the CLI default run mode (dry-run) stated as a requirement and consistent across all spec sections? [Consistency, Spec §FR-031] — Resolved: FR-031 + FR-032 + Key Entities §Run Mode + §Clarifications.
- [x] CHK002 Is the explicit flag that enables write-enabled mode named, or at least required to be unambiguous? [Clarity, Spec §FR-031] — Resolved: FR-031; contracts/cli-slice2.md names the `--write` flag.
- [x] CHK003 Does the spec require dry-run to validate the mapping and produce planned write-back artifacts with zero CRM creates/updates? [Completeness, Spec §FR-031] — Resolved: FR-031 + SC-002/SC-013.
- [x] CHK004 Are "planned write-back artifacts" defined with enough structure to verify dry-run / write-enabled payload parity? [Clarity, Spec §FR-031] — Resolved: planned artifacts = the Slice 1 `*Payload` shapes (US2 scenario 2; contracts/dataverse-adapter.md dry-run capture; data-model §4).
- [x] CHK005 Can "the same payload content" in dry-run vs. write-enabled be objectively compared? [Measurability, Spec §US2] — Resolved: US2 scenario 2 + contracts/dataverse-adapter.md (identical payload shapes).
- [x] CHK006 Is it specified that dry-run still surfaces mapping gaps (does not silently pass)? [Completeness, Spec §US2] — Resolved: US2 scenario 3 + FR-002.
- [x] CHK007 Is it specified that dry-run does not require write credentials, and that their absence is not a dry-run error? [Completeness, Spec §Edge Cases] — Resolved: §Edge Cases + FR-031 + contracts/metadata-discovery-verification.md.
- [x] CHK008 Are requirements defined for an explicit write-enabled run when write credentials are missing? [Coverage, Spec §FR-007] — Resolved: FR-007 (fails for the selected run mode).

## CLI Surface

- [x] CHK009 Is "one CLI invocation processes exactly one queue item" stated precisely? [Clarity, Spec §FR-032] — Resolved: FR-032.
- [x] CHK010 Are the CLI's required inputs (campaign, queue-item selector, fixture, run mode) enumerated? [Completeness, Gap, Spec §FR-032] — Resolved: FR-032 enumerates all five inputs; contracts/cli-slice2.md.
- [x] CHK011 Is the CLI's exit-status contract (success / blocked / failed / resume-needed) defined? [Gap, Clarity] — Resolved: contracts/cli-slice2.md exit-status table + quickstart §9.
- [x] CHK012 Is "operator-visible error/message" defined with a concrete surfacing channel (stderr, exit code, report file)? [Ambiguity, Spec §FR-007] — Resolved by Definitions §Operator-visible.

## Configuration

- [x] CHK013 Are all non-secret mapping-configuration keys (queue fields, status values, task owner mapping, run mode) enumerated? [Completeness, Spec §FR-006] — Resolved: FR-006 + data-model §3 (`slice2.toml` schema).
- [x] CHK014 Are requirements defined for invalid configuration (e.g., a status value that is not a valid option-set member)? [Coverage, Gap, Spec §FR-007] — Resolved: FR-007 + FR-002 + Definitions §Permanent error (option-set mismatch).
- [x] CHK015 Is "callable status" defined as a configurable value with a single source of truth? [Clarity, Spec §FR-011] — Resolved: FR-011 + data-model §3 (`[dataverse] callable_status`).
- [x] CHK016 Does the spec separate non-secret config (file) from secrets (env vars / secret manager) unambiguously? [Clarity, Spec §FR-005] — Resolved: FR-005 + FR-006 + data-model §3.
- [x] CHK017 Are configuration precedence rules (defaults vs. per-queue-item overrides) specified? [Clarity, Spec §FR-025] — Resolved: FR-025 (an approved per-item override supersedes the configured default).

## Secrets Loading

- [x] CHK018 Are all required Dataverse connection secrets enumerated so startup validation can check each one? [Completeness, Spec §FR-005] — Resolved: research §2 + quickstart §2 (`DATAVERSE_TENANT_ID`/`CLIENT_ID`/`CLIENT_SECRET`/`ENV_URL`).
- [x] CHK019 Is the Dataverse authentication method either specified or explicitly and intentionally deferred to planning? [Gap, Spec §FR-005] — Resolved: research §2 (OAuth2 client-credentials via Microsoft Entra ID).
- [x] CHK020 Does the spec require secrets to never be written to logs or exported artifacts? [Completeness, Spec §FR-005] — Resolved: FR-005 + Definitions §Operator-visible.
- [x] CHK021 Are requirements defined for secret values being absent vs. present-but-invalid (distinct failure messages)? [Coverage, Spec §FR-007] — Resolved: FR-007 ("missing, invalid, or unreachable").

## Readiness & Demo Evidence

- [x] CHK022 Does the spec require startup/readiness validation to fail with a clear, operator-visible message when mappings or credentials are missing? [Completeness, Spec §FR-007] — Resolved: FR-007.
- [x] CHK023 Does readiness validation behave consistently across dry-run and write-enabled modes (minus credential checks)? [Consistency, Spec §FR-007] — Resolved: FR-007 ("for the selected run mode") + contracts/metadata-discovery-verification.md.
- [x] CHK024 Is US3 ("Slice 2 setup") reconciled with FR-007 ("startup/readiness validation") — same gate or two distinct steps? [Ambiguity, Spec §US3] — Resolved: plan + contracts/metadata-discovery-verification.md — one-time `discover-crm` discovery vs. per-run `verify`/readiness are two distinct steps.
- [x] CHK025 Are the required end-of-run demo artifacts (updated queue item, Phone Call activity, Task, session result, transcript pointer) each individually specified? [Completeness, Spec §FR-033] — Resolved: FR-033 + quickstart §6.
- [x] CHK026 Is "repeatable demo path" defined with criteria that make repeatability checkable? [Measurability, Spec §FR-033] — Resolved: FR-033 + quickstart (discover → dry-run → write-enabled flow).
- [x] CHK027 Does the spec require the demo outcome to be inspectable without a custom openCloser UI? [Completeness, Spec §FR-033] — Resolved: FR-033 + SC-012.
- [x] CHK028 Is the documented manual cleanup/rollback for the demo CRM record specified? [Gap, Spec §Assumptions] — Resolved: §Assumptions §Demo posture + quickstart §8.

## Notes

- Requirements-quality audit only.
- **Re-verification result: 28/28 resolved.** The plan's run-mode/CLI/config decisions, the `slice2.toml` schema (data-model §3), and contracts/cli-slice2.md close every item — no open run-modes/config defects.
