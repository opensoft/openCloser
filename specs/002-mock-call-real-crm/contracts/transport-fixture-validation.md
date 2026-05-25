# Contract: Mock Transport Fixture Pre-Validation (Addendum)

> Python-flavored pseudo-code for readability; the authoritative contract is the prose.

**Module boundary**: spec FR-019, FR-020; resolves GitHub issue #2
**Implementation**: `src/opencloser/transport/mock.py` (modified)
**Status**: This is an **addendum** to `specs/001-mock-call-mock-crm/contracts/transport.md`.
It is the **only** change permitted to the mock transport module under FR-014 — the
`CallTransport` public surface (`place_call`, `event_stream`) is otherwise unchanged.

---

## Added behavior

`place_call(queue_item, fixture_id)` MUST validate the selected transport fixture **before**
it returns a `mock_provider_call_id` — i.e. before the orchestrator mutates any session
state, the Dataverse queue status, or the attempt count (FR-019).

```text
validate_fixture(fixture_path) -> None        # raises MalformedFixtureError on any failure
```

Validation rejects, with an operator-visible `MalformedFixtureError`:

1. **Invalid JSON** — the fixture file does not parse.
2. **No `events` array** — the parsed object lacks a list-valued `events` key.
3. **Event missing a required identity field** — any event lacks `type`, `event_id`, or
   `timestamp`.

On any rejection the run fails and **no** session row is created, **no** attempt is
consumed, and **no** Dataverse queue update is made (FR-020, SC-006). Because `place_call`
runs before the orchestrator's state mutations, this is structurally guaranteed.

A missing fixture **file** is likewise a `MalformedFixtureError` (same no-mutation outcome).

---

## Unchanged

- `place_call` still returns a globally unique `mock_provider_call_id`.
- `event_stream` is unchanged (one-shot per call id; yields fixture events verbatim,
  including duplicate `event_id`s).
- The transport remains read-only with respect to openCloser state and performs no network
  IO. No Slice-2 / Dataverse knowledge enters this module.

---

## Dependencies

- **Allowed**: as `specs/001/contracts/transport.md` — `opencloser.models`,
  `opencloser.core` primitives, stdlib `json` / `uuid` / `pathlib`.
- **Forbidden**: as `specs/001/contracts/transport.md`, plus any `opencloser.crm.dataverse`
  import.
