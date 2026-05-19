# Implementation Plan: Slice 1 — Mock Call, Mock CRM

**Feature Branch**: `001-mock-call-mock-crm`
**Created**: 2026-05-19
**Spec**: [spec.md](./spec.md)
**Status**: Draft

## Summary

Build the first thin Slice 1 product loop end-to-end against fixtures: one local ALF prospect queue record moves through eligibility, a mock outbound call, a scripted persona conversation, a normalized session result, local state persistence, and mock CRM write-back artifacts including a callback or review task payload when warranted. No SignalWire, no Dataverse, no real LLM. The Slice 1 implementation MUST honor the five module boundaries enumerated in FR-033 so that the future SignalWire transport and Dataverse adapter can swap in without core changes.

## Technical Context

| Aspect | Decision | Source |
|---|---|---|
| Language / runtime | **Python 3.12+** | [research.md §Language](./research.md#language--runtime) |
| Package manager / build | **`uv` + `pyproject.toml` + PEP 621** | [research.md §Build](./research.md#build--package-management) |
| CLI framework | **Typer** | [research.md §CLI](./research.md#cli-framework) |
| State store | **SQLite via stdlib `sqlite3`** (spec mandates SQLite) | spec.md §Assumptions, [research.md §State store](./research.md#state-store) |
| Entity validation / JSON serialization | **Pydantic v2** | [research.md §Validation](./research.md#entity-validation--serialization) |
| Config format | **TOML via stdlib `tomllib`** (`config/slice1.toml` + env-var override) | [research.md §Config](./research.md#configuration-surface) |
| Persona fixture format | **JSON turn-list files** with branching | [research.md §Fixtures](./research.md#persona-fixture-format) |
| Mock transport fixture format | **JSON event-sequence files** | [research.md §Fixtures](./research.md#mock-transport-fixture-format) |
| Artifact directory | **`./artifacts/{session_id}/`** (configurable) | [research.md §Artifacts](./research.md#artifact-directory--filenames) |
| Artifact filenames | **`{session-result\|writeback\|task\|transcript\|conflicting-events\|eligibility-decision}.json`** plus `transcript.txt` | [research.md §Artifacts](./research.md#artifact-directory--filenames) |
| JSON serialization style | **Indented (2-space), sorted keys, UTF-8 no BOM, LF line endings** | [research.md §JSON](./research.md#json-serialization) |
| Schema versioning | **`schema_version: "slice1-v1"`** on every exported JSON artifact | [research.md §Schema](./research.md#schema-versioning) |
| Timestamps | **ISO 8601 / UTC / millisecond precision** (`datetime.now(UTC).isoformat(timespec='milliseconds')`) | spec.md FR-014 |
| `persona_version` format | **`alf-appointment-setter@MAJOR.MINOR.PATCH`** (semver) | [research.md §Persona version](./research.md#persona_version-format) |
| Tests | **pytest** + per-module markers + dependency-direction lint | [research.md §Tests](./research.md#tests--ci-gates) |
| Lint / format | **ruff** (lint + format) | [research.md §Tooling](./research.md#tooling) |

## Constitution Check

The repo currently lacks `.specify/memory/constitution.md` as a standalone file. The spec's `## Constitution Alignment` section codifies the binding principles for this feature; the gate is evaluated against that section.

| Principle | Status | Evidence |
|---|---|---|
| CRM as control plane | ✅ Pass | FR-015 + FR-016 + FR-029 force all write-backs through the mock CRM adapter with the same contract the future Dataverse adapter must satisfy. No parallel UI, campaign builder, or follow-up surface introduced. |
| Thin slice (Slice 1 only) | ✅ Pass | spec.md `## Assumptions → Slice scope` explicitly excludes SignalWire, Pipecat, Dataverse, React/Next.js, multi-worker scaling, Redis/Celery/Kubernetes. The `## Deferred to Implementation Plan` section enumerates execution-level deferrals. |
| Five separable boundaries | ✅ Pass | FR-033 codifies named contract surfaces per module (eligibility, transport, persona, crm-writeback, orchestrator). Project layout (§Project Structure below) maps each to its own package. SC-009 demands per-module isolation against stubs. |
| Safety & human handoff | ✅ Pass | FR-010 + FR-035 + FR-036 codify disclosure timing, DNC honoring, PHI exclusion, enumerated escalation reason codes, and deterministic disposition precedence. |
| Auditability & idempotency | ✅ Pass | FR-019/FR-020/FR-021 + Conflicting Event Audit Record entity + idempotency-key composition. SC-005 + SC-006 enforce zero duplicate-state-change and zero false connected-call activity. |

**Action item carried into Phase 2 tasks**: author `.specify/memory/constitution.md` mirroring the spec's Constitution Alignment section before `/speckit.implement` so future features have a separable governing document. Tracked as a doc task, not a code task.

## Project Structure

Slice 1 introduces the first Python package layout for the openCloser repo. The layout mirrors FR-033's five named boundaries:

```text
.
├── pyproject.toml                  # PEP 621 metadata, deps, ruff/pytest config
├── README.md                        # entry-point doc (future)
├── config/
│   └── slice1.toml                  # call-window, max-attempts, default-tz, artifact-dir
├── src/
│   └── opencloser/
│       ├── __init__.py
│       ├── cli.py                   # Typer entry point (FR-025/FR-026/FR-027)
│       ├── models.py                # Pydantic entity definitions (Queue Item, Session, …)
│       ├── core/                    # FR-033 Interaction Core / Orchestrator
│       │   ├── __init__.py
│       │   ├── orchestrator.py      # session lifecycle; calls the four boundary modules
│       │   ├── idempotency.py       # FR-019 key composition + dedup table
│       │   ├── ids.py               # session_id / mock_provider_call_id generation
│       │   ├── clock.py             # Clock protocol + SystemClock + FrozenClock (FR-014 ISO 8601 UTC ms)
│       │   └── config.py            # TOML + env-var loader → SliceConfig (research.md §Configuration surface)
│       ├── eligibility/             # FR-033 Eligibility evaluator
│       │   ├── __init__.py
│       │   └── evaluator.py         # evaluate(queue_item, config) → EligibilityDecision
│       ├── transport/               # FR-033 Mock call transport
│       │   ├── __init__.py
│       │   ├── base.py              # Transport ABC (FR-008 conceptual contract)
│       │   └── mock.py              # fixture-driven implementation (FR-006)
│       ├── persona/                 # FR-033 Persona module
│       │   ├── __init__.py
│       │   ├── base.py              # Persona ABC
│       │   ├── alf_appointment_setter.py   # the only Slice 1 persona
│       │   ├── disposition_rules.py # FR-036 deterministic precedence
│       │   ├── extraction.py        # FR-034 schema enforcement
│       │   └── escalation.py        # FR-035 reason-code enumeration
│       ├── crm/                     # FR-033 Mock CRM write-back adapter
│       │   ├── __init__.py
│       │   ├── base.py              # WriteBackAdapter ABC (FR-016 conceptual contract)
│       │   └── mock.py              # JSON-artifact-emitting implementation
│       ├── state/                   # SQLite DAO + schema
│       │   ├── __init__.py
│       │   ├── schema.sql           # DDL (see data-model.md)
│       │   └── store.py             # Stateless query/exec wrappers
│       └── artifacts/               # exported-artifact writers
│           ├── __init__.py
│           └── writer.py            # filename pattern, schema_version, ISO 8601 timestamps
├── tests/
│   ├── conftest.py                  # shared fixtures (tmp state store, tmp artifact dir)
│   ├── fixtures/
│   │   ├── queue_items/             # JSON files representing seed queue records
│   │   ├── conversations/           # one JSON per supported disposition (FR-013 / SC-003)
│   │   │   ├── interested_callback_requested.json
│   │   │   ├── interested_email_captured.json
│   │   │   ├── interested_email_and_callback.json   # Q5 Clarifications case
│   │   │   ├── not_interested.json
│   │   │   ├── call_back_later.json
│   │   │   ├── wrong_number.json
│   │   │   ├── do_not_call_mid_call.json
│   │   │   ├── needs_human_review_uncertain_role.json
│   │   │   ├── needs_human_review_email_invalid.json
│   │   │   └── script_truncated.json
│   │   └── transport_events/        # one JSON per non-connected path + duplicates
│   │       ├── no_answer.json
│   │       ├── voicemail.json
│   │       ├── failed.json
│   │       ├── duplicate_connected.json
│   │       ├── duplicate_callback_requested.json
│   │       └── conflicting_failed_after_completed.json
│   ├── unit/
│   │   ├── test_eligibility.py      # @pytest.mark.module(eligibility)
│   │   ├── test_transport_mock.py   # @pytest.mark.module(transport)
│   │   ├── test_persona_rules.py    # @pytest.mark.module(persona)
│   │   ├── test_crm_writeback.py    # @pytest.mark.module(crm)
│   │   └── test_idempotency.py      # @pytest.mark.module(core)
│   └── integration/
│       └── test_end_to_end.py       # @pytest.mark.integration ; per Story 1–3
└── artifacts/                       # gitignored; created at runtime
```

The five-module boundary check (SC-009) is enforced by a CI step that runs each `tests/unit/test_<module>.py` with the rest of the package stub-replaced — see [research.md §Tests](./research.md#tests--ci-gates).

## Phase 0: Outline & Research

See [research.md](./research.md). Resolves every item in the spec's `## Deferred to Implementation Plan` section plus dependency choices not pinned by the spec.

## Phase 1: Design & Contracts

- [data-model.md](./data-model.md) — SQLite DDL for all 10 entities (Queue Item, Eligibility Decision, Session, Mock Call Event, Normalized Result projection, Mock CRM Write-back, Task Payload, Idempotency Key, Conflicting Event Audit Record, Transcript pointer)
- [contracts/orchestrator.md](./contracts/orchestrator.md) — Interaction Core public surface
- [contracts/eligibility.md](./contracts/eligibility.md) — `evaluate(queue_item, config) → EligibilityDecision`
- [contracts/transport.md](./contracts/transport.md) — `place_call(queue_item) → mock_provider_call_id` + event-stream
- [contracts/persona.md](./contracts/persona.md) — `run(session_context, event_stream) → NormalizedResult`
- [contracts/crm-writeback.md](./contracts/crm-writeback.md) — `emit_phone_call_activity`, `emit_queue_status_update`, `emit_task`
- [quickstart.md](./quickstart.md) — operator/dev quickstart

## Phase 2: Task Generation (handoff to `/speckit.tasks`)

The next command (`/speckit.tasks`) will derive an ordered task list from this plan + spec. Expected groupings:

1. **Bootstrap** — `pyproject.toml`, package skeleton, `ruff` + `pytest` config, `.gitignore` for `artifacts/`, `config/slice1.toml` template.
2. **State store** — SQLite schema (`state/schema.sql`), DAO (`state/store.py`), entity Pydantic models (`models.py`).
3. **Eligibility module** — implementation + unit tests covering all 6 rules + multi-rule failure + default-timezone fallback + Story 2 acceptance.
4. **Mock transport** — interface + mock implementation + duplicate-event + conflicting-event handling + Story 3 acceptance.
5. **Persona module** — disposition-rule precedence (FR-036) + extraction schema (FR-034) + escalation reason codes (FR-035) + disclosure validator + one scripted fixture per disposition (SC-003).
6. **Mock CRM write-back** — adapter + payload-shape unit tests (FR-028–FR-031) + queue-status mapping (FR-032).
7. **Interaction Core / Orchestrator** — wires the four modules, applies idempotency (FR-019), increments attempt-count (FR-021), creates blocked sessions (FR-005).
8. **CLI** — Typer entry point, eligibility + run-one-record + artifact-emission (FR-025–FR-027).
9. **Artifact writer** — filename pattern, schema_version stamp, timestamp formatter, atomic write + idempotent re-write.
10. **Integration** — end-to-end fixture-driven runs covering Story 1, Story 2, Story 3, and all SC-001 through SC-009 except SC-008 (deferred to Slice 2 plan time per SC-008's own note).
11. **CI gates** — module-isolation enforcement for SC-009 + lint + type-check (optional) + coverage floor.
12. **Docs** — `.specify/memory/constitution.md` (Slice 1 carry-over task, see Constitution Check action item above), root `README.md` with a 10-line "what is Slice 1".

`/speckit.tasks` will sequence these per dependency, mark P1 vs P2, and produce executable task entries in `tasks.md`.

## Complexity Tracking

| Concern | Status | Mitigation |
|---|---|---|
| Multi-module coordination | Low — Slice 1 is single-record, single-process, no concurrency | Orchestrator is straightforward sequential code |
| Idempotency correctness | Medium — FR-019/FR-020/FR-021 interaction has known sharp edges | Clarifications session locked the precedence; idempotency-key composition is pinned in FR-019; unit tests cover every duplicate/conflict path enumerated in Story 3 |
| Future-slice forward-compat (SC-008) | Medium — must demonstrate without Slice 2 code | Contracts in `contracts/*.md` are language-neutral and reviewed against the future Dataverse / SignalWire intended methods; reviewed at Slice 2 plan time |
| Persona determinism | Low — Slice 1 is scripted only | No randomization, no clock dependency in persona; deterministic precedence rules per FR-036 |
| Cross-platform artifact readability | Low — pinned to UTF-8 / LF / no BOM / ISO 8601 UTC | Codified in `artifacts/writer.py` |

No constitutional gate violations to justify.

## Forward-looking carry-overs to Slice 2

These are not Slice 1 deliverables; they are recorded here so the Slice 2 plan can pick them up cleanly.

- **Transcript `RedactionLayer`**: A new module on the transcript pipeline that runs before disk-write. Default policy: regex + named-entity strip on the PHI keyword set enumerated in FR-010, replaced with `[REDACTED]`. OFF in Slice 1 (no real conversation); ON by default in Slice 2 once real persona output may contain incidental PHI. Per-deployment configurable. Tracked as a Slice 2 backlog item.
- **E.164 phone validation**: Slice 1 accepts "non-null + non-empty after trim" for FR-004(a); Slice 2 tightens to E.164 format validation when real telephony arrives (SignalWire mandates it).
- **Weekday-aware call window**: Slice 1 applies the configured window all 7 days; Slice 2 may add weekday filtering via configuration.
- **`preferred_callback_window` structured parsing**: Slice 1 stores the field verbatim as a free-form string; Slice 2 (scheduling integration) parses to a structured timestamp range.

## Out-of-Scope (Explicit, for reviewer reassurance)

Repeated from spec.md `## Assumptions` and `## Deferred to Implementation Plan` for plan-reviewer convenience:

- No SignalWire, no Pipecat (other than as a stub interface), no Dataverse, no React/Next.js, no admin UI.
- No batch processing, no claim-and-lock, no scheduler.
- No multi-worker scaling, no Redis/Celery/Kubernetes.
- No clinical persona, no PHI collection.
- No live LLM integration — Slice 1 persona is a scripted state machine over fixture transcripts.
- No real telephony, no real outbound traffic of any kind.

These are deferred to Slice 2 and later, per the constitution's binding MVP order.
