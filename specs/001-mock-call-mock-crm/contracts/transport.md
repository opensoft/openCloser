# Contract: Mock Call Transport

> **Note on syntax**: Python-flavored pseudo-code (`name: Type`) is used for readability across the team. Type-hint syntax is decorative; the authoritative contract is the prose description of operations, inputs, and outputs.

**Module boundary**: FR-033, principle #3
**Implementation**: `src/opencloser/transport/base.py` (interface) + `src/opencloser/transport/mock.py` (Slice 1 mock)
**Owns**: call-attempt initiation, event emission, `mock_provider_call_id` assignment, fixture-driven event sequencing
**MUST NOT contain**: persona logic, eligibility logic, write-back logic, business interpretation of events

---

## Public surface

```text
CallTransport (interface):
    place_call(queue_item: QueueItem, fixture: TransportFixture) -> str
        # Returns mock_provider_call_id (globally unique per FR-007).

    event_stream(mock_provider_call_id: str) -> Iterator[MockCallEvent]
        # Yields events in fixture order. Each event carries (event_id, type, timestamp, payload).
```

A second concrete implementation in a future slice will satisfy this same interface against the SignalWire SDK without changes to consumer code (FR-008 conceptual-contract requirement).

---

## Event types (FR-006)

The transport MUST be able to emit, at minimum, the following event types:

- `connected` — call answered; emitted at most once per call attempt
- `no_answer` — terminal; rings out
- `voicemail` — terminal; answered by voicemail
- `failed` — terminal; carrier or transport failure
- `completed` — terminal; persona ended a connected conversation cleanly
- `callback_requested` — non-terminal signal during a connected call (used to assert duplicate-callback-event idempotency per Story 3)

Duplicate-event variants of any of the above MUST be emittable (same `event_id` repeated). The mock transport handles this by reading the fixture file's events array verbatim and yielding each entry unmodified.

---

## Event shape

The runtime `MockCallEvent` model (`src/opencloser/models.py`) carries **five**
fields:

```text
MockCallEvent:
    session_id: str          # See caveat below. The transport has no session_id;
                             # it sets this to the mock_provider_call_id, and the
                             # orchestrator rewrites it to the real session_id on insert.
    event_id: str            # FR-019 idempotency anchor. Unique within (mock_provider_call_id) per emission. Duplicates carry the same id.
    event_type: EventType    # "connected" | "no_answer" | "voicemail" | "failed" | "completed" | "callback_requested"
    received_at: UtcMs       # ISO 8601 UTC ms timestamp
    payload: dict            # opaque to the orchestrator; passed through unchanged
```

> **`session_id` caveat (Slice 1)**: `MockCallEvent` is a single shared type used
> both by the transport (which knows only the `mock_provider_call_id`) and by
> persisted/orchestrator-level event rows (which carry the real `session_id`). In
> Slice 1 the transport sets `session_id = mock_provider_call_id` as a placeholder,
> and the orchestrator rewrites it when it persists each event. Both fields are
> plain `str`, so this substitution is not type-checked. Splitting a session-less
> `TransportEvent` type out of `MockCallEvent` is a deferred Slice 2 cleanup —
> `models.py` is intentionally not changed in Slice 1.

The per-event-type `payload` sub-schema (Q15) is defined in `spec.md` (Mock Call
Event entity); the transport treats `payload` as opaque and yields it verbatim.

---

## Slice 1 mock implementation

`FixtureDrivenTransport` reads a transport fixture (`tests/fixtures/transport_events/<id>.json`) at `place_call(...)` time. The fixture's events are yielded in order via `event_stream(...)`. `place_call` generates a UUID-based `mock_provider_call_id` ensuring global uniqueness.

**Slice 1 simplification — `fixture: TransportFixture` → `fixture_id: str`**: the
public surface above names the second `place_call` parameter `fixture: TransportFixture`
(a fixture object). The Slice 1 runtime signature is `place_call(queue_item, fixture_id: str)`:
the transport receives only a fixture identifier and loads the fixture file from disk
itself. This is a deliberate Slice 1 simplification — the later SignalWire
implementation replaces this parameter with a `dial_plan: DialPlan` object (per the
Forward-compat section). The SC-008 contract review (T075) verifies this is a
parameter-shape change, not a contract-shape change.

`event_stream(...)` is **one-shot per `mock_provider_call_id`**: the pending fixture
mapping is consumed on the first call, so each call id may be streamed exactly once;
a second call (or an id that was never placed) raises `ValueError`. Consumers that
need the events again must persist them — the orchestrator does, on insert.

The transport MUST NOT mutate the queue item or the session. It is read-only with respect to all openCloser state — its only side-effect is yielding events.

---

## Forward-compat with SignalWire (SC-008)

The interface is deliberately minimal:

1. `place_call(queue_item, fixture) -> mock_provider_call_id`
2. `event_stream(mock_provider_call_id) -> Iterator[MockCallEvent]`

The Slice 3 SignalWire implementation will:
- Replace `fixture: TransportFixture` with a `dial_plan: DialPlan` (or similar) parameter; the rest is unchanged.
- Source `mock_provider_call_id` (renamed `provider_call_id` in Slice 3) from the SignalWire SDK.
- Translate SignalWire webhook events into `MockCallEvent` shape (rename to `CallEvent` at Slice 3 time).

The contract review before Slice 3 verifies these are name-only changes, not shape changes (per SC-008). Slice 2 keeps using this mock transport while the CRM adapter becomes real.

---

## Dependencies allowed

- `opencloser.models` (for QueueItem and event shapes)
- `opencloser.core` shared primitives — `ids` for `mock_provider_call_id` generation (the orchestrator contract permits `ids` / `clock` / `idempotency`)
- stdlib `json`, `uuid`, `pathlib`

## Dependencies forbidden

- `opencloser.state` (no persistence — the orchestrator records events)
- `opencloser.persona`, `opencloser.eligibility`, `opencloser.crm`
- Any network IO in Slice 1 (FR-026 dry-run mandate)
