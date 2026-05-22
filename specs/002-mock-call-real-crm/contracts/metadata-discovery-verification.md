# Contract: Dataverse Metadata Discovery & Verification

> Python-flavored pseudo-code for readability; the authoritative contract is the prose.

**Module boundary**: spec FR-001–FR-004, FR-007; constitution §Architecture (verify schema
before any write)
**Implementation**: `src/opencloser/crm/dataverse/metadata.py` (+ `mapping.py`)
**Owns**: one-time metadata discovery that produces the mapping artifact, and the per-run
lightweight verification that gates write-enabled processing
**MUST NOT contain**: write-back logic, eligibility/persona/transport logic

---

## Public surface

```text
discover(client: DataverseClient) -> DataverseMapping
    # Inspects live Dataverse metadata; writes/refreshes config/dataverse_mapping.json.

verify(client: DataverseClient, mapping: DataverseMapping) -> MetadataVerificationReport
    # Read-only, non-mutating. Confirms the mapped schema still matches the artifact.
```

---

## Behavior

### `discover` (one-time — `opencloser discover-crm`)

1. Query Dataverse metadata endpoints (`EntityDefinitions`, `.../Attributes`,
   `GlobalOptionSetDefinitions`) for: the queue-item table, Account, Contact, Campaign,
   Phone Call activity, Task, owner/team, status / DNC / attempt / max-attempts / last-
   disposition / last-session / last-error fields, and the **idempotency-key field** on the
   Phone Call activity and Task.
2. Write/refresh `config/dataverse_mapping.json` (see [data-model.md §2](../data-model.md#2-mapping-artifact--configdataverse_mappingjson)).
   The file is then **PR-reviewed and `_meta.approved` set to `true`** by a human — that
   review is the approval gate for FR-024.
3. If a required table/field/lookup/option-set — including either idempotency-key field —
   cannot be found, `discover` fails and reports every gap (FR-002, SC-007, SC-015).

### `verify` (every write-enabled run)

1. Re-query **only** the entities/attributes/option-sets named in the mapping artifact
   (lightweight — spec Definitions §"Lightweight live verification"). Read-only; never
   regenerates the artifact.
2. Produce `MetadataVerificationReport(ok, missing[], drift[], checked_at)`.
3. `ok == false`, an unverifiable idempotency-key field, an unapproved artifact
   (`_meta.approved != true`), or Dataverse unreachable ⇒ the caller MUST fail before any
   write, report the gap operator-visibly, and touch zero CRM records (FR-002, SC-007).
4. Dry-run runs `verify` too and surfaces gaps, but absent **write** credentials are not a
   dry-run error (FR-031, spec §Edge Cases).

---

## Dependencies

- **Allowed**: `opencloser.crm.dataverse.client` / `.mapping`, `opencloser.models`, stdlib
  `json`.
- **Forbidden**: `opencloser.crm.base`, `opencloser.orchestrator`, `opencloser.persona`,
  `opencloser.transport`, `opencloser.eligibility`.
