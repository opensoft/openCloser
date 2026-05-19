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

```text
MockCallEvent:
    event_id: str            # FR-019 idempotency anchor. Unique within (mock_provider_call_id) per emission. Duplicates carry the same id.
    type: "connected" | "no_answer" | "voicemail" | "failed" | "completed" | "callback_requested"
    timestamp: UtcMs         # ISO 8601 UTC ms
    payload: dict            # opaque to the orchestrator; passed through unchanged
```

---

## Slice 1 mock implementation

`FixtureDrivenTransport` reads a transport fixture (`tests/fixtures/transport_events/<id>.json`) at `place_call(...)` time. The fixture's events are yielded in order via `event_stream(...)`. `place_call` generates a UUID-based `mock_provider_call_id` ensuring global uniqueness.

The transport MUST NOT mutate the queue item or the session. It is read-only with respect to all openCloser state — its only side-effect is yielding events.

---

## Forward-compat with SignalWire (SC-008)

The interface is deliberately minimal:

1. `place_call(queue_item, fixture) -> mock_provider_call_id`
2. `event_stream(mock_provider_call_id) -> Iterator[MockCallEvent]`

The Slice 2 SignalWire implementation will:
- Replace `fixture: TransportFixture` with a `dial_plan: DialPlan` (or similar) parameter; the rest is unchanged.
- Source `mock_provider_call_id` (renamed `provider_call_id` in Slice 2) from the SignalWire SDK.
- Translate SignalWire webhook events into `MockCallEvent` shape (rename to `CallEvent` at Slice 2 time).

The contract review at Slice 2 plan time verifies these are name-only changes, not shape changes (per SC-008).

---

## Dependencies allowed

- `opencloser.models` (for QueueItem and event shapes)
- stdlib `json`, `uuid`, `pathlib`

## Dependencies forbidden

- `opencloser.state` (no persistence — the orchestrator records events)
- `opencloser.persona`, `opencloser.eligibility`, `opencloser.crm`
- Any network IO in Slice 1 (FR-026 dry-run mandate)
