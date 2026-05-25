# Clarification Questions — Slice 2: Mock Call, Real CRM

- **Feature:** `002-mock-call-real-crm`
- **Session:** 2026-05-22
- **Spec:** `specs/002-mock-call-real-crm/spec.md`
- **Questions:** 4 of a 25-max budget (the spec is otherwise thorough)

Answer each question by option letter (e.g. `A`), by saying `recommended`/`yes`
to accept the recommendation, or with your own short answer. You can answer all
at once, e.g. `Q1: A, Q2: A, Q3: A, Q4: A` or `all recommended`.

---

## Q1 — Write-back retry model

**Context:** FR-023 and the Edge Cases require a retry after a transient Dataverse
error (e.g. the Phone Call activity is created but the Task create fails) but do
not say who triggers that retry.

**Recommended:** Option A — bounded auto-retry absorbs transient blips, and
persisted correlation IDs give a crash-safe resume path; matches FR-023/FR-024
and the "Phone Call activity created but Task create fails" edge case.

| Option | Description |
|--------|-------------|
| A | **Auto-retry + resume:** bounded in-run retries with backoff; if still failing, exit with correlation IDs persisted so a later CLI re-invocation resumes the missing writes. |
| B | **Auto-retry only:** bounded in-run retries with backoff, but no resume path — exhausted retries mean re-running the whole item from scratch. |
| C | **Re-invoke to resume:** no automatic retry; on a transient error the run exits and the operator re-invokes the CLI, which resumes from persisted correlation IDs. |

---

## Q2 — Idempotency / duplicate-detection anchor

**Context:** FR-024 leaves this open — "record the CRM correlation identifiers
(or alternate keys)". How the adapter detects an already-written Phone Call
activity or Task is an architecture fork.

**Recommended:** Option A — stamping the session ID onto the CRM record and
pre-querying by it keeps Dataverse authoritative (constitution: CRM is source of
truth) and survives loss of local state, with no dual-path complexity.

| Option | Description |
|--------|-------------|
| A | **Stamp key, pre-query CRM:** write the session ID as an idempotency key onto a Dataverse field of the activity/Task, and pre-query Dataverse by that key before each create. |
| B | **Local correlation store:** rely only on a locally persisted map of session → created Dataverse record IDs; no pre-write query against Dataverse. |
| C | **Both (local + CRM query):** local correlation store is the fast path; a Dataverse query by the stamped key is the fallback when local state is missing or stale. |

---

## Q3 — CLI default run mode

**Context:** The Assumptions call dry-run the "default demo posture", but no
functional requirement makes it the CLI default when no run-mode flag is given.

**Recommended:** Option A — defaulting to dry-run means a forgotten flag can never
mutate Dynamics, matching the stated "dry-run is the safe rehearsal" posture.

| Option | Description |
|--------|-------------|
| A | **Default to dry-run:** no flag = dry-run (zero CRM writes); write-enabled requires an explicit flag. |
| B | **Require explicit flag:** the CLI errors if neither dry-run nor write-enabled is specified, forcing an explicit choice every run. |
| C | **Default to write-enabled:** no flag = write-enabled; dry-run requires an explicit flag. |

---

## Q4 — Metadata discovery vs. verification structure

**Context:** FR-001 verifies live metadata, FR-004 wants a documented mapping
artifact, and the constitution requires verification before any write — but how
these relate across runs is unstated.

**Recommended:** Option A — a one-time discovery step produces the human-reviewed
mapping artifact, while a lightweight per-run live verification satisfies the
constitution's "verified before any write" without full re-discovery each run.

| Option | Description |
|--------|-------------|
| A | **Discover once, verify each run:** a one-time discovery step produces/refreshes the documented mapping artifact (FR-004); every run then does a lightweight live verification of those tables/fields/option-sets before any write. |
| B | **Full discovery each run:** every run performs full metadata discovery and regenerates the mapping artifact from scratch — no separate discovery step. |
| C | **Discover once, trust artifact:** discovery and verification happen once; later runs trust the saved mapping artifact without re-checking live Dataverse metadata. |

---

## Selected Answers

```text
Q1: A
Q2: A
Q3: A
Q4: A
```

### Expanded Notes

- **Q1 — Write-back retry model:** Use bounded in-run auto-retry: initial
  write attempt plus up to 3 retries per Dataverse write operation, with 1s /
  2s / 4s default backoff. A Dataverse `Retry-After` value may replace the next
  delay, capped at 30s. If retry budget is exhausted, persist correlation IDs
  and enough write-back state for a later CLI re-invocation to resume only the
  missing CRM writes.
- **Q2 — Idempotency anchor:** Stamp the session ID or derived idempotency key
  onto a verified Dataverse field on each created Phone Call activity and Task,
  then pre-query Dataverse by that key before each create. This stamped key MUST
  be a real verified Dataverse field, not text buried in a description. If the
  field is missing, write-enabled mode MUST block until the schema/mapping is
  approved.
- **Q3 — CLI default run mode:** Default to dry-run when no run-mode flag is
  provided. Write-enabled CRM mutation requires an explicit flag.
- **Q4 — Metadata verification:** Use a one-time discovery step to produce or
  refresh the human-reviewed mapping artifact, then perform lightweight live
  verification of the mapped tables, fields, lookups, and option-set values
  before every write-enabled run.

### Checklist Defect Resolutions

- **Transient vs. permanent Dataverse errors:** `spec.md` now defines transient
  errors as retryable network timeout/reset, HTTP 408, HTTP 429, and HTTP 5xx;
  permanent errors include validation/auth/authorization/not-found mapping
  failures, option-set mismatch, missing mapping, and metadata drift.
- **Attempt-count timing:** A call attempt is consumed exactly once only after
  eligibility allows the item, write-enabled run-mode checks pass, metadata
  verification passes, and `place_call` succeeds with a pre-validated fixture
  and mock provider call ID. Blocked, dry-run, metadata/readiness failure,
  startup-unreachable, and malformed-fixture paths consume no attempt.
- **Undefined terms:** `spec.md` now defines high-confidence Dataverse value,
  lightweight live verification, operator-visible, transient/permanent
  Dataverse errors, and attempt consumed.
- **`interested_email_captured` coverage:** US1 now has an explicit
  `interested_email_captured` acceptance scenario.
- **Empty queue / multi-item selection:** `spec.md` now requires an explicit
  queue item selector by default, defines deterministic `next ready` selection
  when explicitly used, and defines the empty-queue clean no-op behavior.
- **Dataverse unreachable at start:** US3, FR-002, and the Edge Cases now define
  startup-unreachable behavior as no session, no claim, no transport start, no
  attempt increment, and no CRM write.
