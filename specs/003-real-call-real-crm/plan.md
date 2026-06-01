# Implementation Plan: Slice 3 — Real Call, Real CRM

**Branch**: `003-real-call-real-crm` | **Date**: 2026-05-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-real-call-real-crm/spec.md`

## Summary

Slice 3 keeps the proven Slice 1 / Slice 2 loop (eligibility → call transport → ALF persona →
normalized result → Dataverse write-back) and swaps two things:

1. The **call transport** moves from the fixture-driven mock to a real **SignalWire** outbound
   dialing adapter with provider status / media callbacks normalized into the existing
   `{connected, no_answer, voicemail, failed, completed, callback_requested}` event set
   (FR-004 – FR-008).
2. The **persona runtime** moves from the scripted ALF appointment-setter to a live
   **Pipecat real-time audio runtime** bridged to a deployment-configured **real-time AI
   model provider**, with the deterministic Slice 1 disposition precedence still
   authoritative (FR-013 – FR-016).

A non-blocking **shadow STT lane** runs alongside the live conversation path and emits
discrepancy events for high-value fields (FR-028 – FR-032). A new **rejected-by-authentication
audit log** records forged callback attempts (FR-008, Round 2 Q9), and a deployment-configurable
**post-finalization grace window** lets late shadow discrepancies participate in the disposition
before CRM write-back (FR-029, Round 2 Q7) — without ever delaying live-call finalization.

The technical approach: implement a `SignalWireTransport` behind the unchanged Slice 1
call-transport contract (`place_call(queue_item, dial_plan) → provider_call_id` + normalized
event stream), a `PipecatRuntime` behind the unchanged persona conceptual contract
(`run(session_context, conversation) → PersonaOutput`), and a `ShadowSTTLane` behind a new
shadow STT interface. The Slice 2 `DataverseWriteBackAdapter`, idempotency-key stamping,
bounded retry, and resume coordinator are reused verbatim — Slice 3 adds field-level DNC /
opt-out / blocked / dial-blocked variants under the existing queue-status-update operation
(four-op count preserved, Round 2 Q8) and a **DNC-first ordering** invariant on `do_not_call`
outcomes (Round 2 Q14). The default-safe-mode posture is preserved: the explicit real-call /
write-enabled flag is required on **every** Dataverse-mutating invocation, including resume
(Round 2 Q13). All SignalWire-specific webhook shapes, Pipecat pipeline details, real-time
model provider streaming protocols, and shadow STT provider details remain confined to their
adapter packages and MUST NOT leak into the orchestrator, eligibility evaluator, persona, or
Dataverse adapter (FR-005, FR-013, FR-018, SC-015).

## Technical Context

| Aspect | Decision | Source |
|---|---|---|
| Language / runtime | **Python 3.12+** (`requires-python >=3.12,<3.14`) — unchanged | existing `pyproject.toml`; constitution §Architecture |
| Package manager / build | **`uv` + `pyproject.toml`** (hatchling) — unchanged | Slice 1 / Slice 2 plans |
| Telephony transport | **SignalWire** outbound dialing + status/media webhooks (signature-verified) | spec §Constitution Alignment, FR-004 – FR-008; constitution §Architecture |
| SignalWire SDK / surface | `signalwire` Python SDK for dial + SWML; `httpx` for signature verification + callback ack | [research.md §SignalWire access](./research.md#1-signalwire-outbound-dial--callback-surface) |
| Voice runtime | **Pipecat** real-time audio pipeline bridging SignalWire ↔ configured real-time AI provider | spec FR-013; constitution §Architecture |
| Real-time AI provider | **Deployment-configured** (provider name + model version recorded on the session); first-supported provider chosen at deploy time | spec FR-013, FR-016; [research.md §Realtime AI provider](./research.md#3-real-time-ai-provider-surface) |
| Shadow STT provider | **Deployment-configured** (non-blocking secondary transcript lane) | spec FR-028 – FR-032; [research.md §Shadow STT](./research.md#4-shadow-stt-provider-and-discrepancy-policy) |
| CRM target | **Dynamics 365 / Dataverse Web API** (OData v4) — Slice 2 adapter reused unchanged | spec FR-020; Slice 2 plan |
| CRM auth | **OAuth2 client-credentials** (Microsoft Entra ID) — Slice 2 adapter reused unchanged | Slice 2 plan |
| Mapping artifact | **`config/dataverse_mapping.json`** — Slice 2 artifact reused unchanged | Slice 2 plan |
| Non-secret config | **`config/slice3.toml`** (stdlib `tomllib`) — extends the Slice 1 / Slice 2 TOML pattern | [research.md §Configuration](./research.md#11-configuration-surface) |
| State store | **SQLite** (existing) — extended with five new tables (`rejected_auth_callbacks`, `shadow_stt_discrepancies`, `shadow_lane_truncated_events`, plus the Round 4 `call_events` + `callbacks_audit` DDL) + nine net-new `sessions` columns (incl. the Round 3 `operator_identity_chain_json`); `(session_id, provider_event_id)` dedup is now schema-enforced via a UNIQUE constraint on `call_events`, while `callbacks_audit` is deliberately append-only (no uniqueness) and is also mirrored to the receipt log `callbacks_audit.jsonl` (R4-Q25) | [data-model.md §3](./data-model.md) |
| Persona | **Existing ALF appointment-setter** (Slice 1) — extraction schema, allowed claims, disposition precedence, escalation reason enumeration all reused; **additive** `shadow_stt_discrepancy` reason; clarified disclosure-acknowledgment behavior (no explicit caller ack required) and PHI-volunteered escalation + redaction (Round 2 Q11) | spec FR-014 – FR-016 |
| Testing | **pytest** + contract tests against SignalWire / Pipecat / shadow STT fakes + fixture-replay through the SignalWire transport boundary + recorded-audio playback through the Pipecat runtime + Slice 1 / Slice 2 integration suites still pass | [research.md §Testing](./research.md#12-testing-strategy) |
| Lint / format | **ruff** — unchanged | Slice 1 / Slice 2 plans |
| Run modes | **rehearsal / readiness (default)** vs. **real-call / write-enabled (explicit flag)**; flag required on **every** Dataverse-mutating invocation including resume (Round 2 Q13) | spec FR-001, FR-002, FR-022 |
| New runtime dependencies | `signalwire` SDK, `pipecat-ai`, the chosen real-time AI provider's client, the chosen shadow STT provider's client — confined to adapter packages, not surfaced in core/orchestrator | [research.md](./research.md) |

**Project Type**: Single-project Python CLI (extends the existing `src/opencloser` package
established in Slices 1 and 2). Slice 3 adds new adapter packages — `transport/signalwire/`,
`runtime/pipecat/`, `shadow_stt/`, and a top-level `slice3/` runner — without disturbing the
Slice 1 / Slice 2 boundaries. Constitution §Architecture lists FastAPI as part of the default
stack for future HTTP-surface slices; Slice 3 remains CLI-only — a deliberate slice-scope
decision matching Slice 2.

**Performance / Scale**: One Dataverse queue item per CLI invocation, one ALF campaign.
Slice 3 intentionally does **not** pin numeric latency / throughput / wall-clock targets —
see spec §Deferred to Implementation Plan → "Performance and latency targets" for the full
deferral list (turn latency, time-to-first-audio, abandonment timeout default, silence
timeout default, callback ack timing, finalize timing, shadow-lane processing budget,
back-pressure behavior, resume wall-clock, artifact write throughput, end-to-end invocation
wall-clock). Configurability surfaces (live-call abandonment timeout, silence-after-connection
timeout, post-finalization grace window) are pinned in [research.md §Timeouts](./research.md#7-timeouts-and-grace-window).

**Constraints**: No PHI collection (Constitution §V; spec FR-014, FR-015; caller-volunteered
PHI triggers `phi_collection_risk` + tag-and-redact per FR-015 / FR-033). No secrets in logs
or artifacts (FR-035, SC-018) — and per Round 4 (R4-Q17) the no-secrets guarantee EXTENDS to
exception messages and stack traces: the global exception handler MUST pass any error text
through the redaction layer before it is logged, written to stderr, or written to the run
report. Secrets (incl. the SignalWire callback signing secret) are loaded from the
environment ONLY, at module init — never from disk or CLI argv (FR-035, R4-Q20). Default-on
redaction covers full transcript + session-result summary + shadow STT transcript + shadow STT
discrepancy records (FR-033, Round 2 Q10); transcript pointer metadata excluded so pointers
stay machine-readable. SignalWire callback authentication is mandatory; rejected callbacks
recorded in a distinct audit log with no secret / no body (FR-008, Round 2 Q9). Operator
identity captured locally only; not propagated to Dataverse (FR-016, FR-036, Round 1 Q3 +
Round 2 Q12). No batch, scheduler, multi-worker locking, distributed job queue, or generalized
workflow engine (constitution §II; spec FR-003). Concurrent CLI invocation on the same queue
item is blocked by reusing Slice 2 queue-claim semantics (FR-003, Round 1 Q5).

**Telephony readiness (Round 4 additions to FR-009)**: The FR-009 hard pre-dial readiness
check now also verifies (R4-Q1 / R4-Q23 / R4-Q34): real-time AI provider credentials present
(`realtime_ai_credentials`); shadow-STT provider credentials present when shadow STT is
explicitly enabled via `--shadow-stt` (`shadow_stt_credentials` — when shadow is only
default-on-from-config, a missing key disables the lane with a run-report warning instead of
failing the run); the SignalWire callback signing secret present and loadable (fail-closed —
if signature verification is unavailable the run refuses to start in real-call mode, no
unauthenticated-callback fallback); the status/media callback URL templates carry ONLY the
supported `{session_id}` placeholder (any other placeholder is a readiness failure); and the
Slice 2 Dataverse metadata verification is extended to confirm Dynamics accepts the
`shadow_stt_discrepancy` review-task reason value (option-set membership). Any of these failing
exits before dial (exit 4), consumes no attempt, and is operator-visible.

**Runtime-failure reason codes (Round 4, FR-013)**: The three FR-013 degradation triggers are
recorded in the run report as DISTINCT failure-reason codes — `provider_error` (a),
`runtime_crash` (b), `silence_timeout` (c) (R4-Q13) — so observability can tell them apart.
`RealtimeProviderError` carries a `transient: bool` flag (R4-Q5): a transient pre-connection
provider error is retried within the connect budget and a terminal one finalizes immediately,
but once the call has connected ANY provider error is a degradation trigger regardless of
`transient`.

**Audit retention floor (Round 4, R4-Q33)**: The ≥ 90-day local-artifact retention floor
applies to pointer records and the `artifacts/_unassociated/` tree as well as session-scoped
artifacts; deployment config cannot lower the audit floor below 90 days (if retention config
sets a shorter window, the 90-day floor still wins for audit artifacts).

**Rollback posture (Round 4, R4-Q31)**: Slice 3 is FORWARD-ONLY. The additive SQLite columns
and the new tables are backward-compatible (Slice 2 reads ignore them), so there is NO
automated Slice 3 → Slice 2 downgrade path. The documented rollback is manual: restore a
pre-migration DB snapshot. An already-written-back Dynamics record is never auto-rolled-back.

**Unknowns**: None blocking. The deployment-configurable provider choices (real-time AI
provider, shadow STT provider, timeout defaults) are intentionally **not** spec-level
decisions — they are deployment configuration; representative defaults for development /
CI fakes are pinned in [research.md](./research.md).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Slice 3 disposition | Status |
|---|---|---|
| **I. CRM Is the Control Plane** | Dataverse is the queue source AND the write-back target. The Slice 2 `DataverseWriteBackAdapter`, mapping artifact, idempotency-key stamping, bounded retry, and resume coordinator are reused unchanged. No parallel campaign UI, custom task queue, or replacement CRM is introduced. Operator evidence comes from the updated Dataverse queue item, Phone Call activity, callback / review Task, and local audit artifacts. (Spec §Constitution Alignment "CRM control plane", FR-020.) | ✅ Pass |
| **II. Thin Slices Before Platform Surface** | Target slice: **Slice 3 — Real Call, Real CRM** (the third and final binding MVP slice). Smallest demonstrable outcome: one eligible Dataverse-owned ALF queue item moves from `ready` → final disposition after a real SignalWire call with the correct Dynamics write-back. Slice 3 processes exactly one queue item per invocation (FR-003). Explicitly out of scope: Flutter admin app, multi-provider telephony, batch, distributed job queues, multi-worker coordination, clinical workflows, opportunity creation, custom UI (spec §Assumptions). | ✅ Pass |
| **III. Core, Adapters, and Personas Stay Separate** | Five Slice 1 boundaries preserved (orchestrator / eligibility / call transport / persona / write-back). Three Slice 3 additions are confined behind explicit boundaries: SignalWire-specific webhook shapes / intermediate states confined to `transport/signalwire/`; Pipecat pipeline + real-time AI provider streaming protocol confined to `runtime/pipecat/`; shadow STT provider details confined to `shadow_stt/`. Persona module continues to own disclosure language, allowed claims, extraction schema, deterministic disposition rules, and escalation reasons (FR-014; the live model produces conversation turns and extraction events but MUST NOT change which disposition is selected). SC-015 verifies 0 vendor specifics in core. | ✅ Pass |
| **IV. Automation Is Auditable and Idempotent** | Every processed queue item produces session ID + eligibility decision + real provider call ID + persona version + runtime/model identity + operator identity + started/ended timestamps + final disposition + CRM correlation identifiers. SignalWire status / media callbacks, repeated CLI invocations, and Dataverse write-back retries are idempotent: SC-008 mandates 100% no-duplicate Phone Call activities / Tasks / queue-status transitions / attempt-count increments. The callbacks audit log keyed by `(session_id, provider_event_id)`, the distinct rejected-by-authentication audit log (FR-008 Round 2 Q9), the conflicting-events audit log, and the `shadow_lane_truncated` post-finalization event (Round 2 Q7) provide the duplicate-event, failed-event, blocked-attempt, and retry-behavior verification this principle requires. | ✅ Pass |
| **V. Safety, Privacy, and Human Handoff Are Required Paths** | ALF persona policy preserved from Slices 1 / 2: AI-on-behalf-of-Medx disclosure on every connected call (FR-015), non-clinical scope, no PHI collection, immediate stop on clear opt-out / DNC (FR-024), allowed-claim categories, deterministic disposition precedence (FR-014). Slice 3 adds: hard pre-dial real-call / write-enabled gate (FR-001) including on resume (Round 2 Q13); hard E.164 / provider-acceptable destination phone validation (FR-010); explicit telephony readiness check before every dial (FR-009 – FR-012); caller-volunteered PHI → `phi_collection_risk` escalation + tag-and-redact before write (FR-015 / FR-033, Round 2 Q11); DNC-first write-back ordering on `do_not_call` so a partial-write-back failure still protects the contact (FR-024, Round 2 Q14). Callback and review Tasks remain assigned to the configured Dynamics owner/team. Clinical personas remain out of scope. | ✅ Pass |

**Complexity Tracking**: None. The plan introduces no constitution violations and requires
no Complexity Tracking entries — all Slice 3 additions are confined to adapter boundaries
and reuse the Slice 1 / Slice 2 contracts verbatim where applicable.

**Post-Design Re-Check (after Phase 1 artifacts written — 2026-05-25)**: All five principles
still pass after the Phase 1 design (`data-model.md`, `contracts/`, `quickstart.md`) was
materialised:

- **I. CRM control plane**: Dataverse is the only queue source and write-back target;
  Slice 2 adapter reused unchanged; only additive Phone Call activity fields
  (`provider_call_id`, optional connected-call timestamps) and DNC-first ordering on
  `do_not_call` outcomes ([contracts/crm-writeback-dnc-first.md](./contracts/crm-writeback-dnc-first.md)).
  No parallel system of record introduced.
- **II. Thin slice**: Single-project Python CLI extending existing `src/opencloser/`;
  one queue item per invocation ([contracts/cli-slice3.md](./contracts/cli-slice3.md)
  FR-003); maximum reuse from Slice 1 / Slice 2 ([research.md §14](./research.md#14-reused-slice-1--slice-2-decisions-no-re-research)).
- **III. Boundaries**: Every adapter contract document includes an explicit "What MUST NOT
  leak past this boundary" section AND a contract test asserting non-leakage
  ([signalwire-transport.md](./contracts/signalwire-transport.md),
  [pipecat-runtime.md](./contracts/pipecat-runtime.md),
  [shadow-stt-lane.md](./contracts/shadow-stt-lane.md)).
- **IV. Audit / idempotency**: `Session` row carries `provider_call_id`, `runtime_identity`,
  `operator_identity_{current,original,chain}` (the full ordered resume chain added Round 3),
  `run_mode`, `grace_window_sec`, `finalized_at`; `(session_id,
  provider_event_id)` dedup key on `CallEvent` + `CallbacksAuditLog`; distinct
  `RejectedAuthCallbackLog` (Round 2 Q9); `ShadowLaneTruncatedEvent` audit-only by
  construction ([data-model.md §1, §7](./data-model.md)).
- **V. Safety / handoff**: Real-call flag required on every Dataverse-mutating invocation
  including resume (Round 2 Q13); hard E.164 validation + telephony readiness gate before
  every dial; SignalWire signature verification mandatory with no-secret / no-body audit
  log (Round 2 Q9); caller-volunteered PHI escalates `phi_collection_risk` and tag-and-redacts
  across transcript + summary + shadow transcript + shadow discrepancy records (Round 2
  Q11); DNC-first write ordering on `do_not_call` so partial-failure still protects the
  contact (Round 2 Q14).

No post-design violations. Complexity Tracking remains empty. Plan is ready for
`/speckit-tasks`.

## Round 4 — Checklist-Residual Alignment (2026-06-01)

The Round 4 spec amendments (spec §"Session 2026-06-01 (Round 4 — checklist residual
closure)" + the inline-amended FRs) are propagated into this plan as follows. No
constitution principle changes; all five still pass.

- **Rollback posture (R4-Q31)** — added a "Rollback posture" note to Technical Context /
  Constraints: Slice 3 is FORWARD-ONLY (additive columns + new tables are
  backward-compatible), no automated Slice 3 → Slice 2 downgrade; documented manual rollback
  is restoring a pre-migration DB snapshot; an already-written-back Dynamics record is never
  auto-rolled-back.
- **Telephony readiness (R4-Q1 / R4-Q23 / R4-Q34)** — FR-009 readiness in Constraints now also
  checks real-time AI provider creds, shadow-STT creds (when `--shadow-stt`), signing-secret
  presence (fail-closed when signature verification is unavailable), the `{session_id}`-only
  callback placeholder, and that Dynamics accepts the `shadow_stt_discrepancy` review-task
  reason value.
- **Runtime-failure reason codes (R4-Q13 / R4-Q5)** — FR-013's three triggers are recorded as
  distinct reason codes `provider_error` / `runtime_crash` / `silence_timeout`;
  `RealtimeProviderError` carries a `transient` flag.
- **Security (R4-Q17 / R4-Q20)** — no-secrets now extends to exception messages / stack traces
  (global handler redacts pre-write); secrets are env-only at init (never disk/argv).
- **Audit retention floor (R4-Q33)** — the ≥ 90-day floor applies to pointer records and
  `_unassociated/`; config cannot lower it.
- **State store / DDL (R4-Q25)** — the State-store row now reflects that `call_events` +
  `callbacks_audit` have DDL in data-model §3 (five new tables total), with
  `(session_id, provider_event_id)` dedup now schema-enforced via a UNIQUE constraint on
  `call_events`; the phantom `signalwire_callbacks` name is not reintroduced.

## Project Structure

### Documentation (this feature)

```text
specs/003-real-call-real-crm/
├── plan.md                # This file (/speckit-plan command output)
├── research.md            # Phase 0 output (/speckit-plan command)
├── data-model.md          # Phase 1 output (/speckit-plan command)
├── quickstart.md          # Phase 1 output (/speckit-plan command)
├── contracts/             # Phase 1 output (/speckit-plan command)
│   ├── signalwire-transport.md
│   ├── pipecat-runtime.md
│   ├── shadow-stt-lane.md
│   ├── crm-writeback-dnc-first.md
│   ├── rejected-auth-audit-log.md
│   └── cli-slice3.md
├── checklists/            # /speckit-checklist outputs (R1 + R2, 2039 items / 17 files)
├── clarify-questions.md   # /speckit-clarify (R1 + R2 Q&A record)
├── spec.md
└── tasks.md               # /speckit-tasks output (NOT created by /speckit-plan)
```

### Source Code (extends the existing `src/opencloser` package)

```text
src/opencloser/
├── core/                          # unchanged (orchestrator, ids, clock, config, idempotency)
├── eligibility/                   # unchanged (six Slice 1 rules)
├── persona/                       # extended (extraction.py adds PHI-volunteered handling
│   │                                per Round 2 Q11; disposition_rules.py unchanged;
│   │                                escalation.py adds `shadow_stt_discrepancy` reason)
│   ├── alf_appointment_setter.py
│   ├── base.py
│   ├── disposition_rules.py
│   ├── escalation.py
│   └── extraction.py
├── transport/                     # extended
│   ├── base.py                    # unchanged
│   ├── mock.py                    # unchanged (Slice 1 / Slice 2 fixture-replay path)
│   └── signalwire/                # NEW for Slice 3
│       ├── __init__.py
│       ├── adapter.py             # implements call-transport contract
│       ├── dial.py                # outbound dial + dial_plan construction
│       ├── callbacks.py           # status + media callback handlers + normalization
│       ├── signature.py           # signature verification + rejected-auth audit log
│       └── errors.py
├── runtime/                       # NEW for Slice 3
│   ├── __init__.py
│   ├── base.py                    # PersonaRuntime contract
│   └── pipecat/
│       ├── __init__.py
│       ├── runtime.py             # bridges SignalWire ↔ Pipecat ↔ real-time AI provider
│       ├── pipeline.py            # Pipecat pipeline topology
│       ├── provider.py            # configured real-time AI provider adapter
│       ├── degradation.py         # silence-after-connection timeout + provider-error +
│       │                          # runtime-crash detection (Round 1 Q4 triggers)
│       └── identity.py            # runtime/model identity recording per FR-016
├── shadow_stt/                    # NEW for Slice 3
│   ├── __init__.py
│   ├── base.py                    # ShadowSTTLane contract
│   ├── lane.py                    # non-blocking secondary transcript lane
│   ├── discrepancy.py             # high-value field comparison + policy classification
│   └── truncation.py              # shadow_lane_truncated post-finalization audit event
├── crm/
│   ├── dataverse/                 # Slice 2 adapter — extended for Slice 3:
│   │   ├── adapter.py             #   adds real-provider-call-id + connected-call timestamps
│   │   │                          #   on Phone Call activity; field-level DNC / blocked /
│   │   │                          #   dial-blocked variants under queue-status update;
│   │   │                          #   DNC-first ordering on `do_not_call` (Round 2 Q14)
│   │   └── (others unchanged)
│   ├── base.py                    # unchanged
│   └── mock.py                    # unchanged (Slice 1 fallback / tests)
├── redaction/                     # extended (Round 2 Q10/Q11): default-on redaction now
│   └── layer.py                   # covers full transcript + session-result summary +
│                                  # shadow STT transcript + shadow discrepancy records;
│                                  # pointer metadata excluded; PHI tag-and-redact pass
│                                  # invoked before every artifact write per FR-015
├── artifacts/                     # extended (Round 2): adds rejected-auth audit log writer
│   ├── writer.py                  # adds resume-operator format on run report
│   └── (others unchanged)
├── state/                         # extended (new SQLite tables — see data-model.md)
│   └── store.py
├── slice3/                        # NEW top-level Slice 3 runner
│   ├── __init__.py
│   ├── runner.py                  # end-to-end orchestration for one queue item
│   ├── readiness.py               # telephony readiness check (FR-009 – FR-012)
│   ├── resume.py                  # extends Slice 2 resume: real-call flag required on
│   │                              # every invocation (Round 2 Q13); preserves original
│   │                              # operator + records resuming operator (Round 2 Q12);
│   │                              # answered-but-no-terminal → abandonment (Round 2 Q6)
│   ├── grace_window.py            # post-finalization grace window for CRM write-back
│   │                              # (Round 2 Q7)
│   └── run_report.py              # run report builder (FR-036) with telephony_readiness_
│                                  # summary, rejected-auth count, resume operator format
├── cli.py                         # extended: adds `opencloser run3` subcommand
└── models.py                      # extended with Slice 3 result fields (run-report shape)

tests/
├── contract/                      # extended: contracts for SignalWire transport, Pipecat
│   │                              # runtime, shadow STT lane, DNC-first ordering, rejected-
│   │                              # auth audit log, grace window
├── integration/                   # extended: per-user-story integration tests for US1-US7
│   │                              # plus Round 2 scenarios (Q6 resume / Q7 grace window /
│   │                              # Q9 auth-rejected / Q11 PHI / Q12 multi-operator
│   │                              # resume / Q13 flag absence / Q14 DNC-first)
├── unit/                          # extended: per-module unit tests for slice3/, runtime/
│   │                              # pipecat/, transport/signalwire/, shadow_stt/
└── fixtures/                      # extended:
    ├── signalwire/                # SignalWire webhook payload fixtures (status + media)
    ├── pipecat/                   # recorded audio + extraction-event fixtures
    └── shadow_stt/                # shadow transcript fixtures + discrepancy policy fixtures
```

**Structure Decision**: Single-project Python CLI extending `src/opencloser/`. Slice 3
additions are confined to three new adapter packages (`transport/signalwire/`,
`runtime/pipecat/`, `shadow_stt/`) plus a new `slice3/` runner package and a `runtime/`
abstraction parallel to the existing `transport/`. The Slice 1 `core/`, `eligibility/`, and
`persona/` packages and the Slice 2 `crm/dataverse/` adapter are reused without changes to
their public boundaries — only additive extensions inside their existing public surfaces.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

None. Slice 3 introduces no constitution violations and requires no Complexity Tracking
entries. All five Slice 3 additions (SignalWire transport, Pipecat runtime, shadow STT
lane, rejected-by-authentication audit log, post-finalization grace window) sit behind
explicit module boundaries that preserve the constitution's core/adapter/persona separation
principle. All Slice 1 and Slice 2 contracts are reused verbatim where applicable; the only
Slice-3-sanctioned changes are the name-only renames catalogued in the Slice 1 SC-008
forward-compatibility review (`mock_provider_call_id` → `provider_call_id`, `MockCallEvent` →
`CallEvent`, `fixture_id` → `dial_plan` at the SignalWire transport boundary) and the
additive `shadow_stt_discrepancy` entry in the `human_review_reason` enumeration.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | — | — |
