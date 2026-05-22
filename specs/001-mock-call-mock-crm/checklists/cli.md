# CLI / Operator Interface Requirements Quality Checklist: Slice 1 — Mock Call, Mock CRM

**Purpose**: Validate the quality, clarity, and completeness of requirements for the operator-facing CLI surface (FR-025 / FR-026 / FR-027). Unit tests for the *requirements*, not for the implementation.

**Created**: 2026-05-19
**Feature**: [spec.md](../spec.md) ; [quickstart.md](../quickstart.md)

## Requirement Completeness

- [x] CHK001 - Is the full set of CLI commands enumerated (e.g., `run-one`, `init-state`, `load-queue-item`) with exact argument shapes per command? [Gap, Spec §FR-025]
- [x] CHK002 - Is the "exactly one queue-item ID per invocation" constraint precise about how the ID is supplied (positional arg, `--queue-item-id` flag, env var)? [Gap, Spec §FR-025]
- [x] CHK003 - Are the requirements for the dry-run / fixture-driven mode specified — is it the only Slice 1 mode, or coexists with another? [Completeness, Spec §FR-026]
- [x] CHK004 - Are the four mandatory CLI output fields (eligibility decision, final disposition, mock provider call ID when present, artifact locations) enumerated with exact field labels? [Completeness, Spec §FR-027]
- [x] CHK005 - Are requirements specified for the CLI's exit-code semantics (0 on success, distinct codes for blocked, eligibility errors, transport errors, persona escalation, etc.)? [Gap, Spec §FR-025 + §FR-027]
- [x] CHK006 - Are requirements specified for the CLI's wall-time output (the SC-001 instrumentation field)? [Gap, Spec §SC-001]
- [x] CHK007 - Are requirements specified for the relationship between CLI flags and the configuration surface (do flags override TOML, env vars, both)? [Gap]

## Requirement Clarity

- [x] CHK008 - Is "operator output (CLI output and exported artifacts)" precise about the difference between the two channels (e.g., must the CLI duplicate everything the artifacts contain)? [Ambiguity, Spec §FR-027]
- [x] CHK009 - Is "live demo" in FR-026 defined operationally (suitable for projection, scripted to complete in under 60 seconds, no external services required)? [Clarity, Spec §FR-026]
- [x] CHK010 - Is the CLI's output ordering specified (artifact paths first? disposition first? line-by-line vs. structured)? [Ambiguity, Spec §FR-027]
- [x] CHK011 - Is the FR-027 "minimum" surface defined as exactly those four items, or does it permit additional fields at implementer discretion? [Clarity, Spec §FR-027]

## Requirement Consistency

- [x] CHK012 - Is the CLI command surface consistent with the quickstart's worked examples (e.g., `opencloser run-one --queue-item-id ...`)? [Consistency, Spec §FR-025 + quickstart.md]
- [x] CHK013 - Are CLI flag names consistent with config keys (e.g., is `--max-attempts` the same key as `eligibility.max_attempts` in TOML and `OPENCLOSER_ELIGIBILITY_MAX_ATTEMPTS` in env)? [Consistency, Gap]
- [x] CHK014 - Are the CLI's output field labels consistent with FR-014's normalized-result field names (so an operator can map CLI labels to JSON keys)? [Consistency, Spec §FR-014 + §FR-027]
- [x] CHK015 - Is "demo posture" (Assumptions) consistent with FR-026's "dry-run / fixture-driven mode" (same thing, named twice)? [Consistency, Spec §Assumptions + §FR-026]

## Acceptance Criteria Quality

- [x] CHK016 - Is SC-001's "under 60 seconds end-to-end" measurable from CLI output alone (does the CLI emit a wall-time line, and is that field defined)? [Measurability, Spec §SC-001 + §FR-027]
- [x] CHK017 - Can SC-007 ("operator can explain the outcome without consulting source code") be validated against CLI output alone, or does it require opening artifact files? [Measurability, Spec §SC-007 + §FR-027]
- [x] CHK018 - Is "Operator output MUST surface ... the locations of the exported JSON artifacts" measurable as "every artifact's relative path appears in CLI output exactly once"? [Measurability, Spec §FR-027]

## Scenario Coverage

- [x] CHK019 - Are requirements specified for the CLI output of a blocked-by-eligibility run (no mock_provider_call_id; should the CLI emit "<none>" or omit the line)? [Coverage, Spec §FR-027]
- [x] CHK020 - Are requirements specified for the CLI output of a `failed`-disposition run? [Coverage, Gap]
- [x] CHK021 - Are requirements specified for the CLI output of a `needs_human_review` run (does the human_review_reason appear on the CLI, or only in artifacts)? [Coverage, Gap]
- [x] CHK022 - Are requirements specified for CLI behavior when invoked with an unknown queue-item-id? [Coverage, Gap]
- [x] CHK023 - Are requirements specified for CLI behavior when invoked without any arguments (help text, error, both)? [Coverage, Gap]

## Edge Case Coverage

- [x] CHK024 - Are requirements specified for CLI behavior when the artifact directory cannot be created (permissions, full disk)? [Edge Case, Gap]
- [x] CHK025 - Are requirements specified for CLI behavior when the configuration is invalid or partially missing? [Edge Case, Gap]
- [x] CHK026 - Are requirements specified for CLI behavior under SIGINT / Ctrl-C (graceful shutdown vs. abort vs. leave session in flight)? [Edge Case, Gap]
- [x] CHK027 - Are requirements specified for the CLI's handling of non-TTY environments (CI, log capture)? [Edge Case, Gap]

## Non-Functional Requirements

- [x] CHK028 - Are requirements specified for CLI output encoding (UTF-8 mandatory; how non-ASCII characters in summary/captured_email are presented)? [Gap]
- [x] CHK029 - Are requirements specified for CLI output stability (deterministic output for reruns of the same fixture, supporting golden-file tests)? [Gap, Spec §SC-005]
- [x] CHK030 - Are requirements specified for accessibility of CLI output (e.g., distinguishability without color, screen-reader friendliness)? [Gap]

## Dependencies & Assumptions

- [x] CHK031 - Is the assumption that the CLI is the SOLE operator surface in Slice 1 (no admin UI, no web console) reflected in FR-025 and the Slice scope assumption? [Assumption, Spec §FR-025 + §Assumptions]
- [x] CHK032 - Is the assumption that the operator runs on a developer laptop (per SC-001 "developer laptop" mention) consistent with the CLI's environment expectations? [Assumption, Spec §SC-001]

## Ambiguities & Conflicts

- [x] CHK033 - Is "exported artifacts" vs. "CLI output" reconciled per FR-027 — does the CLI duplicate the artifact filename in its output, or does the operator need to look at filesystem listing? [Ambiguity, Spec §FR-027]
- [x] CHK034 - Is the relationship between FR-025 (CLI exists) and FR-026 (dry-run mode) precise — is dry-run a flag, the default, or always-on in Slice 1? [Ambiguity, Spec §FR-025 + §FR-026]
