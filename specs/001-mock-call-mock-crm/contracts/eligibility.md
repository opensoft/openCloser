# Contract: Eligibility Evaluator

> **Note on syntax**: Python-flavored pseudo-code (`name: Type`) is used for readability across the team. Type-hint syntax is decorative; the authoritative contract is the prose description of operations, inputs, and outputs.

**Module boundary**: FR-033, principle #2
**Implementation**: `src/opencloser/eligibility/evaluator.py`
**Owns**: the six FR-004 rules, the default-timezone fallback, and the persisted EligibilityDecision shape
**MUST NOT contain**: transport events, persona logic, write-back logic, queue mutation logic

---

## Public surface

```text
EligibilityEvaluator (interface):
    evaluate(queue_item: QueueItem, config: SliceConfig, clock: Clock) -> EligibilityDecision
```

The concrete Slice 1 implementation is `BuiltinEligibilityEvaluator` in `evaluator.py`. Future slices may swap in alternate evaluators behind this same interface (e.g., an evaluator that consults an external DNC list).

---

## Behavior

The evaluator MUST evaluate ALL six rules on every call (FR-004 — no short-circuit) and return an `EligibilityDecision` populated with per-rule pass/fail. Rule order is canonical (a)–(f):

| Rule | Definition |
|---|---|
| (a) phone presence | `queue_item.phone_number is not None and queue_item.phone_number.strip() != ""` |
| (b) usable timezone | `queue_item.timezone` resolves via `zoneinfo.ZoneInfo(...)` OR `config.eligibility.default_timezone` was substituted |
| (c) call window | `now_in_local_tz` falls within `[config.call_window.start, config.call_window.end]` (inclusive both ends; minute resolution) |
| (d) DNC | `queue_item.dnc_flag is False` |
| (e) max attempts | `queue_item.attempt_count < config.eligibility.max_attempts` |
| (f) callable status | `queue_item.callable_status == CallableStatus.READY` |

Outcome:
- `outcome='allow'` iff all six rules pass.
- Otherwise `outcome='block'` and `failing_rules` lists every failing rule letter in canonical order.

Default-timezone fallback (FR-004(b), Edge Case "Missing or malformed timezone"):
- If `queue_item.timezone` is None or unparseable, the evaluator MUST set `default_tz_substituted_for` to the original (possibly None) value AND use `config.eligibility.default_timezone` for rule (c). Rule (b) then PASSES (a usable timezone was obtained via fallback).

---

## Input shape

```text
QueueItem (from data-model.md):
  queue_item_id, facility_name, phone_number?, timezone?, default_tz_applied, email?,
  attempt_count, dnc_flag, callable_status, last_decision_at?

SliceConfig:
  call_window: { start: "HH:MM", end: "HH:MM" }
  eligibility: { max_attempts: int, default_timezone: IANA-tz-name }
```

## Output shape

`EligibilityDecision` per data-model.md. Notable fields:

- `decision_id` (UUID)
- `queue_item_id`
- `decided_at` (ISO 8601 UTC ms)
- `outcome` ∈ {`allow`, `block`}
- six `rule_*_pass` booleans
- `failing_rules` list (only populated when `outcome='block'`)
- `default_tz_substituted_for` (only populated when fallback applied)
- `session_id` (assigned by the orchestrator AFTER session creation; the evaluator returns the decision with `session_id` unset and the orchestrator backfills)

---

## Determinism & purity

The evaluator MUST be pure with respect to its inputs (queue_item + config + clock-derived `now`). It MUST NOT read from or write to the state store directly — it returns a value object and the orchestrator persists.

---

## Dependencies allowed

- `opencloser.models`
- stdlib (`zoneinfo`, `datetime`)

## Dependencies forbidden

- `opencloser.state` (persistence is the orchestrator's job)
- `opencloser.persona`, `opencloser.transport`, `opencloser.crm`
- Anything network or IO that isn't reading config
