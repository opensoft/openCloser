# Implementation Plan: Slice 2 — Mock Call, Real CRM

**Branch**: `002-mock-call-real-crm` | **Date**: 2026-05-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-mock-call-real-crm/spec.md`

## Summary

Slice 2 keeps the proven Slice 1 loop (eligibility → mock call → scripted ALF persona →
normalized result → write-back) and swaps the **CRM** from a local mock to **Dynamics 365 /
Dataverse**. Dataverse becomes the queue source and the write-back target; the local SQLite
store is demoted to session, audit, artifact, and CRM-correlation storage.

The technical approach: implement a **`DataverseWriteBackAdapter`** behind the unchanged
Slice 1 `WriteBackAdapter` interface (`contracts/crm-writeback.md`) and a
**`DataverseQueueLoader`** behind the unchanged `QueueItem` contract, so the orchestrator,
eligibility evaluator, mock transport, and persona stay vendor-neutral. All Dataverse field
names, lookups, option-set values, and owner/team IDs are confined to a new
`crm/dataverse/` package and resolved through a discovered, verified **mapping artifact**.
Slice 2 also adds three smaller pieces: a default-on transcript **`RedactionLayer`** before
disk writes, **fixture pre-validation** in the mock transport (resolving GitHub issue #2),
and a **dry-run/write-enabled** run-mode split with a CLI-level **resume coordinator** for
idempotent recovery from partial Dataverse write-back.

## Technical Context

| Aspect | Decision | Source |
|---|---|---|
| Language / runtime | **Python 3.12+** (`requires-python >=3.12,<3.14`) | existing `pyproject.toml`; constitution §Architecture |
| Package manager / build | **`uv` + `pyproject.toml`** (hatchling) — unchanged | Slice 1 plan |
| New runtime dependency | **`httpx`** (Dataverse Web API + OAuth token POST) — the only new runtime dep | [research.md §Dataverse access](./research.md#1-dataverse-web-api-access) |
| CRM target | **Dynamics 365 / Dataverse Web API** (OData v4, `/api/data/v9.2/`) | spec §Constitution Alignment; constitution §Architecture |
| CRM auth | **OAuth2 client-credentials** (Microsoft Entra ID app registration); secrets from env vars | [research.md §Auth](./research.md#2-dataverse-authentication) |
| Mapping artifact | **`config/dataverse_mapping.json`** — discovered, verified, PR-reviewed | [research.md §Mapping artifact](./research.md#4-mapping-artifact-format) |
| Non-secret config | **`config/slice2.toml`** (stdlib `tomllib`) — extends the Slice 1 TOML pattern | [research.md §Config](./research.md#5-configuration-surface) |
| State store | **SQLite** (existing), extended with `crm_correlations` + `writeback_progress` tables | [data-model.md](./data-model.md) |
| Call transport | **Existing fixture-driven mock transport**, plus FR-019/FR-020 pre-validation | spec FR-012, FR-019 |
| Persona | **Existing scripted ALF appointment-setter** — unchanged | spec FR-012, FR-014 |
| Testing | **pytest** + contract tests (adapter vs. `crm-writeback.md`) + integration vs. an in-process **Dataverse fake** (no live CRM in CI) | [research.md §Testing](./research.md#9-testing-strategy) |
| Lint / format | **ruff** — unchanged | Slice 1 plan |
| Run modes | **dry-run (default)** vs. **write-enabled (explicit `--write`)** | spec FR-031 |

**Project Type**: Single-project Python CLI (extends the Slice 1 `src/opencloser` package).

**Performance/Scale**: One queue item per CLI invocation, one ALF campaign. Not
latency-critical; the only timing constraint is the bounded write-back retry budget
(initial + 3 retries, 1s/2s/4s backoff, `Retry-After` capped at 30s — FR-023).

**Constraints**: No real telephony, no live audio, no real-time model. No batch, scheduler,
multi-worker locking, or job queue. Dataverse is the only CRM target. CRM writes gated
behind explicit `--write`; metadata verified before every write-enabled run.

**Unknowns**: None blocking. Environment-specific Dataverse logical names and option-set
values are intentionally **not** spec-level decisions — they are discovered at runtime and
recorded in the mapping artifact (spec §Assumptions; FR-001/FR-004). No `NEEDS
CLARIFICATION` remain after the 2026-05-22 clarification session.

## Constitution Check

*GATE: evaluated against `.specify/memory/constitution.md` v1.0.0 — before Phase 0 and again after Phase 1.*

| Principle | Status | Evidence |
|---|---|---|
| **I. CRM is the control plane** | ✅ Pass | Dataverse is the queue source (`DataverseQueueLoader`, FR-008) and the write-back target (`DataverseWriteBackAdapter`, FR-015). Local SQLite is demoted to session/audit/artifact/correlation only (spec §Assumptions). No parallel campaign UI, custom task queue, or replacement CRM (FR-033 — Dynamics is the operator surface). |
| **II. Thin slice** | ✅ Pass | Target slice = "Mock call, real CRM" (#2 of the binding MVP order). Out-of-scope platform work (SignalWire, Pipecat, real-time model, batch, scheduler, multi-worker, Redis/Celery/K8s, custom UI, multi-CRM) is enumerated in spec §Assumptions and design.md §Non-Goals. |
| **III. Core / adapter / persona boundaries** | ✅ Pass | All Dataverse detail is confined to `crm/dataverse/` (FR-016, SC-010). The orchestrator, eligibility evaluator, mock transport, and persona are reused unchanged except for FR-019 fixture pre-validation (FR-014). New boundaries (`DataverseQueueLoader`, `DataverseWriteBackAdapter`, `RedactionLayer`) sit behind existing contracts. |
| **IV. Auditable & idempotent** | ✅ Pass | Correlation IDs recorded locally **and** stamped on Dataverse records (FR-024); duplicate events, repeated invocations, and retries produce no duplicate records (FR-021–FR-023, SC-005); bounded retry is simple inline retry, **not** advanced retry orchestration (no Celery/queue/scheduler — constitution-compliant). Resume completes only missing writes (FR-023, SC-014). |
| **V. Safety, privacy & human handoff** | ✅ Pass | Persona safety unchanged (AI disclosure, non-clinical, no PHI, DNC stop). Slice 2 adds default-on transcript redaction before disk writes (FR-028–FR-030) and owner-assigned callback/review Tasks (FR-025–FR-026). DNC updates DNC/opt-out fields and creates no Task (FR-027). |
| **Architecture constraints** | ✅ Pass | Stack stays Python 3.12 + stdlib + Pydantic + Typer; only `httpx` is added (constitution explicitly blesses `httpx`). Secrets from env vars; logs avoid secrets (FR-005). Transcript retention is deployment-configurable incl. summary-only (FR-030). CRM schema verified before any write (FR-001/FR-002); high-confidence CRM values preserved (FR-003). |
| **Delivery workflow** | ✅ Pass | Spec defines 6 independently testable user stories. This plan records: target slice, queue source + write-back target, mock transport, persona versioning (unchanged), eligibility/DNC/call-window behavior (unchanged), structured result + write-back, idempotency keys, human handoff, and verification evidence (below). |

**Verification evidence required before completion**: unit tests per new module; **contract
tests** proving `DataverseWriteBackAdapter` satisfies `contracts/crm-writeback.md` unchanged
(SC-011); integration tests against an in-process **Dataverse fake** covering US1–US6;
fixture pre-validation tests (SC-006); a dry-run then a write-enabled **manual demo** against
one dedicated test campaign record (SC-001, SC-002, SC-012).

**Result: PASS — no violations. Complexity Tracking is empty.**

## Project Structure

### Documentation (this feature)

```text
specs/002-mock-call-real-crm/
├── plan.md                # This file
├── research.md            # Phase 0 — decisions & rationale
├── data-model.md          # Phase 1 — SQLite additions, mapping-artifact + config schemas, Pydantic models
├── quickstart.md          # Phase 1 — operator/dev quickstart (discover → dry-run → write-enabled)
├── contracts/             # Phase 1 — Slice 2 module contracts
│   ├── dataverse-adapter.md
│   ├── dataverse-queue-loader.md
│   ├── metadata-discovery-verification.md
│   ├── redaction-layer.md
│   ├── transport-fixture-validation.md
│   └── cli-slice2.md
├── checklists/            # requirements-quality checklists (already generated)
└── tasks.md               # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

Slice 2 **adds** packages and makes **two narrow modifications** to existing modules; it
does not restructure the Slice 1 layout.

```text
src/opencloser/
├── cli.py                      # MODIFIED — add `discover-crm` + `run-crm` commands, run-mode flags
├── crm/
│   ├── base.py                 # UNCHANGED — WriteBackAdapter ABC (the Slice 2 contract surface)
│   ├── mock.py                 # UNCHANGED — Slice 1 mock adapter
│   └── dataverse/              # NEW — all Dataverse-specific code lives here (SC-010 boundary)
│       ├── __init__.py
│       ├── adapter.py          # DataverseWriteBackAdapter — implements WriteBackAdapter
│       ├── client.py           # DataverseClient — httpx Web API client + bounded transient retry
│       ├── auth.py             # OAuth2 client-credentials token acquisition
│       ├── metadata.py         # discovery (one-time) + lightweight live verification
│       ├── mapping.py          # DataverseMapping — load mapping artifact, translate fields
│       ├── queue_loader.py     # DataverseQueueLoader — Dataverse row → QueueItem contract
│       └── errors.py           # TransientDataverseError / PermanentDataverseError
├── redaction/                  # NEW — transcript redaction boundary
│   ├── __init__.py
│   └── layer.py                # RedactionLayer + RegexRedactionPolicy / NoOpPolicy / summary-only
├── slice2/                     # NEW — Slice 2 CLI-level coordination (keeps orchestrator unchanged)
│   ├── __init__.py
│   ├── runner.py               # dry-run vs write-enabled coordination around process_one_queue_item
│   └── resume.py               # resume coordinator — completes missing write-back ops only
├── transport/
│   └── mock.py                 # MODIFIED — FR-019/FR-020 fixture pre-validation in place_call
├── state/
│   ├── schema.sql              # MODIFIED — add crm_correlations + writeback_progress tables
│   └── store.py                # MODIFIED — DAO for the two new tables
├── artifacts/
│   └── writer.py               # MODIFIED — route transcript text through RedactionLayer
├── core/                       # UNCHANGED — orchestrator, idempotency, ids, clock, config
├── eligibility/                # UNCHANGED
├── persona/                    # UNCHANGED
└── models.py                   # MODIFIED (additive only) — Slice 2 Pydantic models

config/
├── slice1.toml                 # UNCHANGED
├── slice2.toml                 # NEW — run mode, callable status, task-owner map, redaction policy, retry tunables
└── dataverse_mapping.json      # NEW — discovered + verified mapping artifact (FR-004), PR-reviewed

tests/
├── fixtures/dataverse/          # NEW — recorded Dataverse responses + fake-CRM seed data
├── unit/                        # NEW — test_dataverse_adapter, _metadata, _mapping, _queue_loader,
│                                #        _redaction, _transport_fixture_validation, _resume
├── contract/                    # NEW — DataverseWriteBackAdapter vs contracts/crm-writeback.md (SC-011)
└── integration/                 # NEW — US1–US6 end-to-end against the in-process Dataverse fake
```

**Structure Decision**: Single-project layout, extending `src/opencloser`. The
`crm/dataverse/` package is the **sole** location of Dataverse vendor detail (enforced by
SC-010 boundary test). A new `slice2/` package holds run-mode and resume coordination so the
Slice 1 orchestrator contract (FR-014) is preserved unchanged — the orchestrator is reused
as-is, called by `slice2/runner.py`.

## Phase 0 — Outline & Research

See [research.md](./research.md). Resolves: Dataverse Web API access library, OAuth
client-credentials auth, metadata discovery/verification mechanics, mapping-artifact format,
configuration surface, transient-error classification + retry, the idempotency-key field and
pre-query, the resume design that keeps the orchestrator unchanged, the redaction layer, the
fixture pre-validation placement, and the testing strategy (Dataverse fake).

## Phase 1 — Design & Contracts

- [data-model.md](./data-model.md) — `crm_correlations` + `writeback_progress` SQLite
  tables; `dataverse_mapping.json` schema; `slice2.toml` schema; new Pydantic models
  (`DataverseMapping`, `RunMode`, `RedactionPolicyConfig`, `CrmCorrelation`,
  `WriteBackProgress`, `MetadataVerificationReport`).
- [contracts/dataverse-adapter.md](./contracts/dataverse-adapter.md) — Dataverse concrete
  implementation of the unchanged `crm-writeback.md` interface, incl. idempotency pre-query
  and bounded retry.
- [contracts/dataverse-queue-loader.md](./contracts/dataverse-queue-loader.md) — Dataverse
  row → `QueueItem` contract; selector semantics.
- [contracts/metadata-discovery-verification.md](./contracts/metadata-discovery-verification.md)
  — one-time discovery + per-run lightweight verification.
- [contracts/redaction-layer.md](./contracts/redaction-layer.md) — `RedactionLayer`
  interface and policies.
- [contracts/transport-fixture-validation.md](./contracts/transport-fixture-validation.md)
  — the FR-019/FR-020 addendum to `specs/001/contracts/transport.md`.
- [contracts/cli-slice2.md](./contracts/cli-slice2.md) — `discover-crm` / `run-crm`
  commands, run modes, inputs, exit-status contract.
- [quickstart.md](./quickstart.md) — operator/dev quickstart.

The Slice 1 `contracts/crm-writeback.md` and the `QueueItem` portion of the eligibility
contract are **reused unchanged** — Slice 2 adds concrete implementations behind them.

## Phase 2 — Task Generation (handoff to `/speckit-tasks`)

`/speckit-tasks` will derive an ordered `tasks.md`. Expected groupings:

1. **Bootstrap** — add `httpx` dependency; `config/slice2.toml`; `tests/fixtures/dataverse/`.
2. **State store** — `crm_correlations` + `writeback_progress` schema + DAO.
3. **Dataverse client** — `auth.py` (client-credentials), `client.py` (Web API + transient retry), `errors.py`.
4. **Metadata** — discovery + lightweight verification; mapping-artifact load/write.
5. **Queue loader** — Dataverse row → `QueueItem`; selector semantics; empty-queue no-op.
6. **Write-back adapter** — `DataverseWriteBackAdapter` + idempotency pre-query; **contract tests** (SC-011).
7. **Transport hardening** — FR-019/FR-020 fixture pre-validation (issue #2).
8. **Redaction** — `RedactionLayer` + policies; artifact-writer integration.
9. **Slice 2 runner & resume** — run-mode coordination + resume coordinator.
10. **CLI** — `discover-crm` + `run-crm` commands; dry-run default.
11. **Integration** — US1–US6 against the Dataverse fake; SC-001…SC-015.
12. **Docs** — `quickstart.md` finalization, demo cleanup runbook, close GitHub issue #2.

## Complexity Tracking

*No constitutional gate violations. This section is intentionally empty.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| — | — | — |
