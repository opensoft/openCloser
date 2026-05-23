# Contract: Dataverse Queue Loader

> Python-flavored pseudo-code for readability; the authoritative contract is the prose.

**Module boundary**: spec FR-008–FR-011; constitution principle I, III
**Implementation**: `src/opencloser/crm/dataverse/queue_loader.py`
**Owns**: loading one ALF queue item from Dataverse and translating it into the **unchanged**
Slice 1 `QueueItem` contract consumed by the eligibility evaluator
**MUST NOT contain**: eligibility-rule logic, write-back logic, persona/transport logic

---

## Public surface

```text
DataverseQueueLoader:
    load(selector: QueueSelector) -> QueueItem | None
        # Returns a QueueItem mapped from Dataverse, or None for an empty queue.

QueueSelector = ExplicitId(queue_item_id: str) | NextReady(campaign: str)
```

`QueueItem` is the Slice 1 Pydantic shape — **unchanged**. The loader is the only place that
knows it came from Dataverse.

---

## Behavior

1. **Explicit ID** selector — GET the queue row by GUID.
2. **Next-ready** selector — GET callable rows for the campaign, deterministically ordered:
   earliest `next_attempt_at`, then oldest CRM-created timestamp, then queue-item GUID as a
   stable tie-breaker (FR-008, spec §Edge Cases). Take the first.
3. **Empty queue** — when no row matches, return `None`; the caller exits as a clean no-op
   ("no callable queue item"), creating no session and writing nothing (FR-009).
4. **Translate** the Dataverse row → `QueueItem` via `DataverseMapping`: facility/Account,
   phone, timezone, attempt count, max attempts, DNC/opt-out, callable status, last
   disposition, last session ID, last error. Option-set integers are mapped to their
   conceptual values.
5. The loader is **read-only** — it never claims, mutates, or marks the row in-progress. The
   in-progress mark happens later, after eligibility + run-mode + fixture pre-validation pass
   (FR-010), and only in write-enabled mode.

A queue item not in the configured callable status, or with a missing phone number, is
**not** filtered out here — it is loaded and passed on so the eligibility evaluator records a
blocked result (FR-011). A malformed (non-empty) phone number is loaded as-is; the
data-quality warning is raised downstream (FR-034).

---

## Dataverse Web API addressing

Dataverse exposes a table under two different names that the loader MUST keep
distinct:

- **Logical name** (singular, e.g. `account`, `medx_callqueueitem`) — used by the
  metadata endpoints (`EntityDefinitions(LogicalName='...')`).
- **Entity-set name** (often plural, e.g. `accounts`, `medx_callqueueitems`) — used
  by record CRUD URLs (`/api/data/v9.2/<entity_set>(id)` and query collections).

Both come from the `DataverseMapping` artifact's `entities` map (`logical_name` and
`entity_set_name` fields). The loader uses `entity_set_name` for record GETs and
falls back to `logical_name` only when the mapping omits the set name (legacy /
minimal scaffolds).

---

## Dependencies

- **Allowed**: `opencloser.models` (`QueueItem`), `opencloser.crm.dataverse.client` /
  `.mapping`, stdlib.
- **Forbidden**: `opencloser.eligibility`, `opencloser.persona`, `opencloser.transport`,
  `opencloser.crm.base`; leaking any Dataverse logical name outside `crm/dataverse/` (SC-010).
