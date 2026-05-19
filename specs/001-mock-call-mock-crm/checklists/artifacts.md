# Artifacts & Operator UX Requirements Quality Checklist: Slice 1 — Mock Call, Mock CRM

**Purpose**: Validate the quality, clarity, and completeness of requirements for exported JSON artifacts, transcript storage, CLI output, filename conventions, and operator inspectability. Unit tests for the *requirements*, not for the implementation.

**Created**: 2026-05-19
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [ ] CHK001 - Is the list of exported artifact files (session-result JSON, mock CRM write-back JSON, task-payload JSON, transcript file, eligibility-decision JSON if separate) fully specified for every run outcome (success, blocked, no_answer, voicemail, failed, do_not_call, needs_human_review)? [Completeness, Spec §FR-023]
- [ ] CHK002 - Is the filename convention that allows correlation by session ID specified precisely (prefix, suffix, separator, directory layout)? [Gap, Spec §FR-023] → **RESOLVED-BY-Research §Artifact directory & filenames (plan-level)**
- [ ] CHK003 - Is the artifact-export directory's location specified (default path, override mechanism, per-run subdirectory vs. flat)? [Gap, Spec §FR-023] → **RESOLVED-BY-Research §Artifact directory & filenames (plan-level)**
- [ ] CHK004 - Are the requirements for the CLI output surface (eligibility decision, final disposition, mock_provider_call_id, artifact paths) enumerated with the exact fields that MUST appear? [Completeness, Spec §FR-027]
- [ ] CHK005 - Are the contents of the per-session transcript file specified (raw fixture content, structured turns, summary embedded, metadata header)? [Gap, Spec §Clarifications] → **RESOLVED-BY-Research §Persona fixture format + §Artifact directory (plan-level)**
- [ ] CHK006 - Are the requirements specified for an artifact that records the conflicting late events held for audit (per FR-020) — is this exported as JSON or only persisted internally? [Gap, Spec §FR-020 + §FR-023] → **RESOLVED-BY-FR-020 (tightened) + Conflicting Event Audit Record entity + Research §Artifact directory (`conflicting-events.json`)**
- [ ] CHK007 - Is the eligibility-decision artifact specified as a separate exported JSON (so Story 2's "read the block reason from the exported artifacts" is satisfied), or is it embedded inside session-result.json? [Gap, Spec §FR-023 + §Story 2] → **RESOLVED-BY-Research §Artifact directory (`eligibility-decision.json` is a separate file)**

## Requirement Clarity

- [ ] CHK008 - Is "readable JSON artifacts" defined (pretty-printed, indented, schema-versioned, UTF-8, sort key order)? [Ambiguity, Spec §FR-023]
- [ ] CHK009 - Is the `transcript_pointer` path's resolution rule specified (relative to artifact directory, relative to repo root, absolute, URI scheme)? [Clarity, Spec §Clarifications + §FR-014]
- [ ] CHK010 - Is "minimize sensitive data" in FR-024 quantified with concrete examples (no API keys, no PHI patterns, transcript redaction rules)? [Ambiguity, Spec §FR-024]
- [ ] CHK011 - Is the CLI output format defined (plain text per line, structured key=value, JSON, mixed) and is "surfaces, at minimum" precise about ordering and emphasis? [Clarity, Spec §FR-027]
- [ ] CHK012 - Is "the locations of the exported JSON artifacts" in FR-027 specified — must the CLI emit absolute paths, relative paths, or both? [Clarity, Spec §FR-027]

## Requirement Consistency

- [ ] CHK013 - Is the artifact set produced on a blocked-by-eligibility run consistent across FR-012 ("normalized session result for every processed queue record, including blocked"), FR-023 (the artifact list), Story 2 acceptance ("read the block reason from the exported artifacts"), and the SC-002 "no Phone Call-like activity" exclusion? [Consistency, Spec §FR-012 + §FR-023 + §Story 2]
- [ ] CHK014 - Are the "summary-only" and "pointer-based" transcript modes consistently described across FR-014, FR-024, the Transcript / Transcript Pointer entity, the Assumptions section, and the Clarifications log? [Consistency, Spec §Clarifications]
- [ ] CHK015 - Are filenames described consistently across the spec — does every reference to "session-result JSON" / "write-back JSON" / "task-payload JSON" use the same canonical file-naming convention? [Consistency, Gap]
- [ ] CHK016 - Is the requirement that artifact filenames allow correlation by session ID (FR-023) consistent with the per-session-file transcript-pointer scheme (Clarifications) — i.e., do all four artifact kinds share the same session-ID-keyed prefix? [Consistency, Spec §FR-023 + §Clarifications]

## Acceptance Criteria Quality

- [ ] CHK017 - Can SC-007 ("operator can explain the outcome without consulting source code") be evaluated by a non-implementer following a written walkthrough of the exported artifacts? [Measurability, Spec §SC-007]
- [ ] CHK018 - Are SC-001's "session result JSON" and "mock CRM write-back JSON" file-name or path patterns specified well enough to verify their presence with a single glob after a run? [Measurability, Spec §SC-001]
- [ ] CHK019 - Are the FR-014 fields measurable by direct inspection of session-result JSON keys (not requiring decoding or cross-referencing other artifacts)? [Measurability, Spec §FR-014]

## Scenario Coverage

- [ ] CHK020 - Are requirements specified for artifact output when a run aborts unexpectedly (persona crashes, fixture missing, state-store write fails)? [Coverage, Gap]
- [ ] CHK021 - Are requirements specified for re-running a previously-run queue-item ID — are artifacts overwritten, suffixed with a new session ID, or rejected with an error? [Coverage, Gap]
- [ ] CHK022 - Are requirements specified for the artifact output of a `needs_human_review` run, including the `human_review_reason` field's location and the review task payload's filename? [Coverage, Spec §FR-014 + §Story 4]
- [ ] CHK023 - Are requirements specified for the CLI output when a blocked-by-eligibility run produces no Phone Call-like activity (so "mock_provider_call_id (when present)" is absent)? [Coverage, Spec §FR-027]
- [ ] CHK024 - Are requirements specified for the artifact output of a run that completes but produces no task payload (e.g., `not_interested`) — which files exist, which don't? [Coverage, Spec §FR-018]

## Edge Case Coverage

- [ ] CHK025 - Are requirements specified for handling of artifact-directory write conflicts (existing files with the same name, permission errors, full disk)? [Edge Case, Gap]
- [ ] CHK026 - Are requirements specified for what the operator sees on the CLI when no artifacts are produced (e.g., transport-level early failure before any state is persisted)? [Edge Case, Gap]
- [ ] CHK027 - Are requirements specified for transcript file encoding (UTF-8 mandatory), line endings (LF vs. CRLF), and BOM handling to ensure cross-platform readability? [Edge Case, Gap]
- [ ] CHK028 - Are requirements specified for the maximum size of any single artifact (e.g., transcript file ceiling) to prevent runaway scripted fixtures? [Edge Case, Gap]
- [ ] CHK029 - Are requirements specified for the artifact's handling of non-ASCII characters in `summary` or `captured_email` (escape vs. embed)? [Edge Case, Gap]

## Non-Functional Requirements

- [ ] CHK030 - Are requirements specified for a schema-versioning marker in the exported JSON (so future format changes are detectable)? [Gap, Spec §FR-023] → **RESOLVED-BY-Research §Schema versioning (`schema_version: "slice1-v1"` on every artifact)**
- [ ] CHK031 - Are requirements specified for the artifact's stability across reruns of the same fixture (deterministic ordering of keys, deterministic timestamps when feasible)? [Gap, Spec §FR-023]

## Dependencies & Assumptions

- [ ] CHK032 - Is the assumption that exported artifacts are the canonical demo surface for Slice 1 (Demo posture assumption) documented and tied to SC-007? [Assumption, Spec §Assumptions + §SC-007]
- [ ] CHK033 - Is the dependency on a writable local filesystem (vs. an in-memory or remote store) acknowledged in the artifact requirements? [Assumption, Spec §FR-022 + §FR-023]

## Ambiguities & Conflicts

- [ ] CHK034 - Is the requirement to "minimize sensitive data" (FR-024) reconciled with the default pointer-based transcript storage (which writes the full scripted transcript to a separate file under the artifacts directory)? [Conflict, Spec §FR-024 + §Clarifications]
- [ ] CHK035 - Is the requirement for "readable" artifacts (FR-023) reconciled with possible binary or large-blob fields (e.g., voicemail audio in a future slice) — what does "readable" mean for non-textual fields? [Ambiguity, Spec §FR-023]
- [ ] CHK036 - Is the relationship between FR-014's session-result fields and the CLI's "Operator output" surface (FR-027) precise — does the CLI display every field, a subset, or a summary view? [Ambiguity, Spec §FR-014 + §FR-027]
