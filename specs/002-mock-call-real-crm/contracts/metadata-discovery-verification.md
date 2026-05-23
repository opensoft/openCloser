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
discover(
    client: DataverseClient,
    scaffold: DataverseMapping,
    *, now_utc_ms: str,
) -> DataverseMapping
    # Scaffold-driven re-inspection: confirms every entity/field/option-set value in
    # `scaffold` against live Dataverse metadata and returns a refreshed mapping
    # artifact (updated `_meta.discovered_at`, `_meta.approved` reset to False).
    # The CLI (`opencloser discover-crm`) writes the result to
    # `config/dataverse_mapping.json`.

verify(
    client: DataverseClient,
    mapping: DataverseMapping,
    *, now_utc_ms: str,
) -> MetadataVerificationReport
    # Read-only, non-mutating. Confirms the mapped tables, fields, AND option-set
    # integer values still exist and match in live Dataverse.
```

---

## Behavior

### `discover` (one-time, scaffold-driven — `opencloser discover-crm`)

`discover` is **scaffold-driven**, not greenfield: the conceptual-to-logical field
assignment (which conceptual field maps to which Dataverse logical name) is a human-
reviewed decision (FR-004), so a starter scaffold (a hand-edited or previous
`config/dataverse_mapping.json`) is the input. `discover` then re-inspects live
Dataverse and confirms every entity/field/option-set value in the scaffold:

1. For every entity in the scaffold, query the metadata endpoint
   (`EntityDefinitions(LogicalName='X')` and `.../Attributes`) and confirm the table
   exists and carries each mapped attribute's logical name (including the
   idempotency-key fields on the Phone Call activity and Task).
2. For every option-set member in the scaffold, query the picklist metadata
   (`Microsoft.Dynamics.CRM.PicklistAttributeMetadata`) and confirm the mapped
   integer value is present in the live picklist.
3. Refresh `_meta.discovered_at` and reset `_meta.approved` to `False` (a fresh
   discovery requires PR re-approval before write-enabled use — FR-024).
4. If any mapped entity, attribute, or option-set value cannot be confirmed,
   `discover` raises `MetadataError` naming every gap (FR-002, SC-007, SC-015).
5. The CLI (`opencloser discover-crm`) writes the returned mapping to
   `config/dataverse_mapping.json` (see
   [data-model.md §2](../data-model.md#2-mapping-artifact--configdataverse_mappingjson));
   a human reviewer then sets `_meta.approved = true` in a PR — that PR review is
   the approval gate for FR-024.

**Note (scope decision):** greenfield discovery — building a mapping from scratch
against an unfamiliar Dataverse environment with no scaffold — is intentionally out
of scope for Slice 2 because the conceptual-to-logical assignment is a human design
choice. Deployments start from the checked-in scaffold (or copy and adapt another
deployment's mapping).

### `verify` (every write-enabled run)

1. Re-query **only** the entities/attributes/option-sets named in the mapping
   artifact (lightweight — spec Definitions §"Lightweight live verification").
   Read-only; never regenerates the artifact.
2. Confirm each mapped entity exists, each mapped attribute exists on its entity,
   AND each mapped option-set integer is present in the live picklist.
3. Produce `MetadataVerificationReport(ok, missing[], drift[], checked_at)`.
4. `ok == false`, an unverifiable idempotency-key field, an unapproved artifact
   (`_meta.approved != true`), or Dataverse unreachable ⇒ the caller MUST fail
   before any write, report the gap operator-visibly, and touch zero CRM records
   (FR-002, SC-007).
5. Dry-run runs `verify` too and surfaces gaps, but absent **write** credentials
   are not a dry-run error (FR-031, spec §Edge Cases).

---

## Dependencies

- **Allowed**: `opencloser.crm.dataverse.client` / `.mapping`, `opencloser.models`, stdlib
  `json`.
- **Forbidden**: `opencloser.crm.base`, `opencloser.orchestrator`, `opencloser.persona`,
  `opencloser.transport`, `opencloser.eligibility`.
