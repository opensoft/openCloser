# SC-008 Plan-Time Review — Slice 1 → Slice 2 Forward-Compat

**Reviewer**: (Slice 1 implementation team)
**Date**: 2026-05-19
**Source spec**: [spec.md](./spec.md) · **Source plan**: [plan.md](./plan.md)

## Purpose

SC-008 mandates: "The mock CRM adapter's payload shapes and method surface are reused unchanged by the planned Slice 2 work, demonstrating that the conceptual contract held when swapping the mock CRM adapter for the real Dataverse adapter (forward-looking criterion verified at Slice 2 plan time)."

This document is the Slice 1-time review of the conceptual contracts in `contracts/*.md`, evaluating each against the *intended* shape of the Slice 2 substitutions (real SignalWire transport + real Dataverse CRM + real persona runtime). Verification is name-only-vs-shape-only at this stage; the runtime check lands when Slice 2 actually arrives.

## Methodology

For each Slice 2 substitution, walk the corresponding `contracts/*.md`'s **Public Surface** and **Forward Compatibility** sections, and identify:

1. **Name-only changes** (acceptable; just renames at Slice 2 plan time)
2. **Shape changes** (NOT acceptable; would invalidate SC-008 and require a Slice 1 amendment)

## Reviews

### 1. Mock Call Transport → SignalWire (per [contracts/transport.md](./contracts/transport.md))

| Surface element | Slice 1 form | Slice 2 substitution | Verdict |
|---|---|---|---|
| `place_call(queue_item, fixture_id) -> mock_provider_call_id` | sync fn returns string | `place_call(queue_item, dial_plan) -> provider_call_id` | **Name-only change** (fixture_id → dial_plan; mock_provider_call_id → provider_call_id) |
| `event_stream(call_id) -> Iterator[MockCallEvent]` | sync generator over JSON fixture | same; backed by SignalWire webhook handler | **Name-only change** (MockCallEvent → CallEvent) |
| `MockCallEvent` fields: `(session_id, event_id, event_type, received_at, payload)` — **5 fields** (authoritative: runtime `src/opencloser/models.py`) | fixed | Same field set; `payload` may add `provider_raw` sub-key | **Shape-stable** — Slice 2's `provider_raw` is additive |
| Event types `{connected, no_answer, voicemail, failed, completed, callback_requested}` | enum | SignalWire produces a superset; Slice 2 maps to this enum at the transport boundary | **Shape-stable** — translation happens inside the adapter |

**Verdict**: ✅ The transport contract is forward-compatible. Slice 2 maps SignalWire webhooks into `MockCallEvent` shape; consumer code (orchestrator) needs no changes.

> **Doc-drift note (Slice 1 cleanup)**: the runtime `MockCallEvent` model (`src/opencloser/models.py`) carries **5 fields** — `session_id, event_id, event_type, received_at, payload`. The `contracts/transport.md` Public Surface still shows the pre-implementation 4-field sketch (`event_id, type, timestamp, payload`). This is a stale-doc discrepancy, not a shape regression — the table row above uses the authoritative runtime field set. `contracts/transport.md` should be reconciled to the 5-field runtime model at Slice 2 plan time.

### 2. Mock CRM Write-back → Dataverse (per [contracts/crm-writeback.md](./contracts/crm-writeback.md))

| Surface element | Slice 1 form | Slice 2 substitution | Verdict |
|---|---|---|---|
| `emit_phone_call_activity(payload)` | INSERT into local SQLite | POST to Dataverse Phone Call entity | **Name-only** (no signature change) |
| `emit_queue_status_update(payload)` | INSERT into local SQLite | PATCH the Dataverse-managed queue row | **Name-only** |
| `emit_task(payload)` | INSERT into local SQLite | POST to Dataverse Task entity, mapping `task_kind` to subtype | **Name-only** |
| `PhoneCallActivityPayload` fields | **9 fields** — FR-028's 8 + `schema_version` (runtime `models.py`) | Dataverse Phone Call entity has additional fields (e.g., regarding, owner) that the adapter populates from session context | **Shape-stable** — Dataverse can be a *superset* of Slice 1 fields; the consumer-facing shape is unchanged |
| `QueueStatusUpdatePayload` fields | **7 fields** — FR-029's 6 + `schema_version` (runtime `models.py`) | Same; Dataverse queue-status update is a delta operation | **Shape-stable** |
| `TaskPayload` fields | **12 fields** — FR-030's 10 (incl. Q19 `assigned_to`) + `schema_version` + `task_id` (runtime `models.py`) | `assigned_to` is the Slice 2 wiring point for the Dataverse owner | **Shape-stable** — `assigned_to` is Slice 1-optional, Slice 2-required |
| FR-018 belt-and-suspenders in `emit_task` | adapter looks up session disposition + no-ops on exclusion set | Same; the Slice 2 Dataverse adapter inherits this safety net | **Shape-stable** |

**Verdict**: ✅ The CRM write-back contract is forward-compatible. The Slice 2 Dataverse adapter implements the same three `emit_*` methods over the same three payload Pydantic classes (renamed to drop the `Mock` prefix if desired). The `assigned_to` carve-out from Clarifications Q19 is the explicit Slice 2 wiring point.

### 3. Persona → Real persona runtime (per [contracts/persona.md](./contracts/persona.md))

| Surface element | Slice 1 form | Slice 2+ substitution | Verdict |
|---|---|---|---|
| `Persona.run(session_context, conversation) -> PersonaOutput` | sync, scripted, deterministic | async streaming, LLM-backed; same return shape | **Shape-stable** for outputs; `conversation` input may need a streaming variant |
| `PersonaOutput` fields | 6 fields | Same | **Shape-stable** |
| `Extraction` schema (FR-034) | 7 fields, enum-typed | Same; LLM produces these via structured-output | **Shape-stable** |
| Disposition rules (FR-036) | 10 ordered rules, code | Code remains the authoritative rule list; LLM's role is purely extraction | **Shape-stable** — *FR-036 is intentionally kept out of the LLM* to preserve auditability |
| Disclosure validator | exact-match canonical string | Soft-match (the future LLM may paraphrase, but a future spec amendment would lift this) | **Name-only change at amendment time** — Slice 1 wording is the audit anchor |

**Verdict**: ✅ The persona contract is forward-compatible. The future LLM-backed persona implements the same `run(...)` method over the same `PersonaOutput`/`Extraction` shapes. The disposition rules and FR-035 escalation reasons remain in deterministic code (a deliberate audit invariant — see constitution Principle 4).

### 4. Eligibility (no Slice 2 substitution planned)

Per the spec's Assumptions, Slice 2 does not change eligibility — same evaluator, same six rules. No SC-008 concern here.

### 5. Interaction Core / Orchestrator (no Slice 2 substitution planned)

The orchestrator is the integration point that gets *more* capability with each slice but does not get replaced. SC-008 does not apply.

## Summary

| Boundary | SC-008 Verdict |
|---|---|
| Mock Call Transport → SignalWire | ✅ Forward-compatible (name-only changes) |
| Mock CRM Write-back → Dataverse | ✅ Forward-compatible (name-only changes; `assigned_to` is the wiring point) |
| Persona → real runtime | ✅ Forward-compatible (LLM does extraction; disposition rules stay in code) |
| Eligibility | N/A — no Slice 2 substitution |
| Interaction Core | N/A — orchestrator extends, doesn't get replaced |

**No Slice 1 amendments are required**. SC-008 holds at plan-time review. The final runtime verification will occur during Slice 2 implementation when the real Dataverse adapter is wired and the orchestrator + write-back code paths are exercised against it unchanged.

## Sign-off

Reviewed at the close of Slice 1 implementation, with the Slice 2 substitution targets recorded in plan.md `## Forward-looking carry-overs to Slice 2`. Any future deviation from the verdicts above must trigger a Slice 1 spec amendment or be addressed in the Slice 2 plan.
