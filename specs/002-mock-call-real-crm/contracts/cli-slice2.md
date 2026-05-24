# Contract: Slice 2 CLI & Run Coordination

> Python-flavored pseudo-code for readability; the authoritative contract is the prose.

**Module boundary**: spec FR-031–FR-033, FR-007; constitution principle II
**Implementation**: `src/opencloser/cli.py` (modified) + `src/opencloser/slice2/runner.py`
+ `src/opencloser/slice2/resume.py`
**Owns**: the Slice 2 CLI commands, run-mode selection, and the coordination that calls the
**unchanged** Slice 1 orchestrator and drives resume
**MUST NOT contain**: Dataverse logical names (those stay in `crm/dataverse/`), persona/
eligibility logic, or any modification to the orchestrator contract (FR-014)

---

## Commands

```text
opencloser discover-crm
    # One-time metadata discovery → writes config/dataverse_mapping.json (FR-001/FR-004).

opencloser run-crm [--write] (--queue-item-id ID | --next-ready)
                   [--campaign C]
                   --transport-fixture PATH --conversation-fixture PATH
    # Processes exactly one Dataverse queue item (FR-032).
```

**Run mode (FR-031)**: no `--write` ⇒ **dry-run** (the default — validate mapping, produce
planned write-back artifacts, zero CRM writes). `--write` ⇒ **write-enabled**. There is no
way to mutate CRM without `--write` (SC-013).

**Required inputs (FR-032)**: campaign selector, queue-item selector (explicit ID or
`--next-ready`), transport fixture, conversation fixture, run mode (defaulted).

---

## Behavior — `run-crm`

`slice2/runner.py` coordinates, calling the Slice 1 orchestrator unchanged:

1. Startup/readiness validation — config + (write mode only) secrets (FR-007).
2. `verify` Dataverse metadata; on failure, fail before any write (FR-002).
3. `DataverseQueueLoader.load(selector)` — empty queue ⇒ exit `no-callable-item`, no-op (FR-009).
4. Construct the boundary objects: the existing `EligibilityEvaluator`, the existing mock
   `CallTransport`, the existing `Persona`, and — as the `WriteBackAdapter` — the
   `DataverseWriteBackAdapter` (write mode) or a dry-run capture adapter (dry-run mode).
5. Call `process_one_queue_item(...)` — the orchestrator is **unchanged** (FR-014); it sees
   only the contract interfaces.
6. Map the `RunReport` to a CLI exit status; write the local session-result + (redacted)
   transcript artifacts.

## Behavior — resume

When a write-enabled run exits `resume_needed` (retry budget exhausted mid-write-back),
re-invoking the same command triggers `slice2/resume.py`:

- It reads `writeback_progress` + `crm_correlations` + the persisted write-back payloads,
  and re-issues **only** the missing `emit_*` calls through the `DataverseWriteBackAdapter`
  (whose idempotency pre-query makes each replay safe).
- It does **not** re-run `process_one_queue_item` and does not re-place the mock call —
  keeping the orchestrator contract untouched and producing no duplicate records (FR-023,
  SC-014).
- A re-invocation for an already-`completed` session is a clean no-op (FR-021).
- A re-invocation for a `blocked`-by-conflict session (T045) does NOT auto-resume — the conflict re-read runs first; if the conflict is still present, the run exits `blocked` again with the same `block_reason`. The operator reconciles the Dataverse record manually (restoring the session-owned in-progress state if appropriate, or accepting the human change) before a fresh `run-crm` invocation can complete the missing writes. Abandonment is the absence of a follow-up run; the persisted `writeback_progress` row remains as audit evidence per FR-035.

---

## Exit-status contract

| Status | Meaning |
|---|---|
| `completed` | loop finished; write-back done (or planned, in dry-run) |
| `blocked` | eligibility/metadata block (SC-008) — no call placed — OR mid-run CRM-state conflict (T045) — partial `writeback_progress` persisted, already-completed approved writes preserved, human-changed values left unchanged. The run-report `block_reason` field disambiguates conflict from eligibility/metadata. |
| `no-callable-item` | empty queue — clean no-op (FR-009) |
| `resume_needed` | transient failure exhausted retry budget — re-invoke to resume |
| `failed` | malformed fixture or permanent error — no attempt consumed (SC-006) |

All non-`completed` statuses are operator-visible per the spec Definitions §"Operator-visible"
(CLI result + exit status + local run report), never leaking secrets or CRM record contents.

---

## Dependencies

- **Allowed**: `opencloser.slice2.*`, `opencloser.core.orchestrator` (call only, unchanged),
  `opencloser.crm.dataverse.*`, `opencloser.crm.base`, `opencloser.redaction`,
  `opencloser.transport`, `opencloser.eligibility`, `opencloser.persona`,
  `opencloser.artifacts`, `opencloser.state`, `typer`.
- **Forbidden**: modifying the orchestrator/eligibility/persona/transport contracts;
  Dataverse logical names outside `crm/dataverse/` (SC-010).
