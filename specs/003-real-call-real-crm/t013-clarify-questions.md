# T013 — Clarifying Questions (SignalWire transport contract test)

**Created**: 2026-05-25 · **Task**: T013 — `tests/contract/test_signalwire_transport.py` (10 assertions from `contracts/signalwire-transport.md`) · **Status**: answered 2026-05-25

These questions resolve design decisions needed BEFORE T013's test code is meaningful. None
of them are answered by spec.md, plan.md, research.md, or `contracts/signalwire-transport.md`.
The contract names the assertions; these questions pin down the surface the assertions
will run against.

---

## Q1 — Dedup / ordering flags on `CallEvent`

The contract test names reference `is_duplicate=True`, `out_of_order=True`, and
`late_after_finalization=True` on the normalized `CallEvent`. Today `CallEvent = MockCallEvent`
(models.py:235, 1103) and `MockCallEvent` has **none** of those fields — only `session_id`,
`event_id`, `event_type`, `received_at`, `payload`. Where should those flags live?

- **A.** Add three optional `bool` fields to `MockCallEvent` (also exposed via `CallEvent`).
  Lowest churn; same model serves Slice 1 / 2 / 3. Risk: Slice 1 / 2 tests that assert
  `extra="forbid"` validate-on-input may need to be checked.
- **B.** Define a new `Slice3CallEvent(MockCallEvent)` subclass in `models.py` with those three
  bool fields; transport returns the subclass; orchestrator type-checks against the base.
  Keeps Slice 1 / 2 surface frozen.
- **C.** Carry the flags in a sibling `CallbackDeduplicationContext` object emitted alongside
  the event (separate stream channel). Largest blast radius on the orchestrator.
- **D.** Encode them as well-known keys inside the existing `payload: dict[str, Any]` field
  on `MockCallEvent` (and document the allow-list in `_ALLOWED_PAYLOAD_KEYS`). No model change.

**Answer: A.** Add optional `bool` fields to `MockCallEvent`: `is_duplicate`,
`out_of_order`, and `late_after_finalization`, all defaulting to `False`.
`CallEvent` is the normalized event contract, so the transport should be able to mark delivery
state without changing the orchestrator's event-stream shape. Keep these flags out of `payload`;
payload should remain provider-neutral event data, and the existing payload allow-list should not
become a hidden metadata channel for transport bookkeeping.

## Q2 — Where dedup / out-of-order state lives

The contract says the transport MUST de-duplicate by `(session_id, provider_event_id)`. Which
surface owns the state the contract test inspects?

- **A.** **Adapter-local in-memory set** keyed by `(session_id, provider_event_id)` for the
  lifetime of one `SignalWireTransport` instance. Simplest; resume after restart wouldn't
  benefit. (Acceptable per Round 2 Q6 — resume immediately finalizes as abandonment.)
- **B.** **SQLite-backed** `signalwire_callbacks` table (data-model.md §1.5). Survives
  process restart; contract test reads the table directly to assert ledger state.
- **C.** **Both** — adapter-local set is the dedup gate, then write to `signalwire_callbacks`
  for audit / replay. Most defensible; matches the existing audit-log pattern.

**Answer: C.** Use both. The adapter-local set is the immediate dedup gate for the current
`SignalWireTransport` instance and makes `event_stream` deterministic. A SQLite
`signalwire_callbacks` audit surface is the durable ledger for replay/debug evidence and should
be the state surface T013 pins. If the current schema does not yet include that table, the T013
red should make that missing callback ledger visible; do not overload `rejected_auth_callbacks`
for accepted provider callbacks.

## Q3 — How the test drives callback delivery into the transport

The contract is async (`AsyncIterator[CallEvent]`) and references HTTP 401 for forged
signatures. How does the test feed simulated SignalWire callbacks?

- **A.** **Public ingestion method** on the adapter (e.g.,
  `await adapter.ingest_callback(headers, body)`) that the test calls directly. No HTTP layer
  in the contract test; HTTP layer covered by a future integration test.
- **B.** **In-process ASGI** — the test spins up the embedded FastAPI callback receiver per
  research §1 and POSTs to it via `httpx.AsyncClient(app=...)`. Exercises signature verify +
  HTTP code end-to-end.
- **C.** **Module-level helper** like `transport.signalwire.callbacks.normalize(headers, body)`
  that returns the normalized `CallEvent` or raises `SignatureVerificationError`. Pure function
  surface; HTTP code asserted via the exception type's `http_status` attribute.

**Answer: A.** Add a public async adapter method such as
`await adapter.ingest_callback(headers, body)`. The contract test should avoid the HTTP receiver
while still exercising the real transport boundary: signature verification, provider-event-id
extraction, normalization, dedup/out-of-order classification, audit append, and event-stream
enqueueing. The future FastAPI or ASGI callback receiver can call this same method in integration
tests.

## Q4 — How `place_call` is exercised without burning SignalWire credentials

The contract test must run in CI. Which mocking surface?

- **A.** **Constructor-injected SignalWire `Client`** — adapter takes `client: SignalWireClient`
  as a dep; test passes a `FakeSignalWireClient` from `tests/fixtures/signalwire/`.
- **B.** **`respx`** to intercept the SDK's outbound `httpx` calls. Add `respx` to dev deps.
- **C.** **Monkey-patch `signalwire.rest.Client`** in `transport/signalwire/dial.py` via
  `monkeypatch.setattr` in the test. No new dep, no DI refactor.

**Answer: A.** Constructor-inject the SignalWire client dependency and use a
`FakeSignalWireClient` in contract tests. This keeps CI credential-free, avoids adding `respx`
solely to intercept SDK internals, and gives the production adapter an explicit seam for testing
dial success, provider rejection, and SDK/network failures without brittle monkey-patching.

## Q5 — Test failure mode (TDD red)

T022–T026 implement the actual transport; T013 runs first and must fail. Two ways to "fail":

- **A.** **Import-time failure** — T013 imports `from opencloser.transport.signalwire.adapter
  import SignalWireTransport`. Test collection errors until the module exists. Honest TDD red,
  but `pytest --collect-only` is noisy.
- **B.** **Assertion-time failure** — T013 also lays down stub modules (`adapter.py`,
  `errors.py`, `signature.py`, `callbacks.py`) that import cleanly but raise `NotImplementedError`
  in every method. Tests collect and run; each fails with a clear `NotImplementedError`.
  T022–T026 then replace the stub bodies.

**Answer: B.** Prefer assertion-time failures with importable stub modules. Collection should stay
clean, and each red test should fail at the unimplemented behavior it is pinning. T022-T026 can
then replace the stub bodies without first repairing noisy import failures.

## Q6 — `pytest-asyncio` dependency

`event_stream` is `AsyncIterator[CallEvent]`. Existing Slice 1 / Slice 2 tests are largely sync.
Slice 3 needs async test support.

- **A.** Add `pytest-asyncio>=0.23` to `[dependency-groups].dev` in `pyproject.toml`; configure
  `asyncio_mode = "auto"` so `async def test_*` works without per-test `@pytest.mark.asyncio`.
- **B.** Add `pytest-asyncio` with **strict** mode and require each async test to declare
  `@pytest.mark.asyncio`. Explicit but more boilerplate.
- **C.** Skip `pytest-asyncio` — wrap each async test body in `asyncio.run(...)`. No new dep.

**Answer: B.** Add `pytest-asyncio` and use strict mode with explicit `@pytest.mark.asyncio` on
async tests. Slice 3 has several async boundaries, so the tests should make async behavior
visible at the test declaration instead of relying on implicit auto mode or ad hoc
`asyncio.run(...)` wrappers.

## Q7 — Scope of `test_signature_verification_does_not_log_secret_or_body`

The contract says the rejected-auth audit log must contain only
`(received_at, source_metadata, http_status)` — never the signing secret, never the body.
Where does the test read that audit?

- **A.** **SQLite** — query `rejected_auth_callbacks` directly and assert the row schema +
  that no column contains `os.environ["SIGNALWIRE_SIGNING_SECRET"]` or body bytes.
- **B.** **JSONL artifact** — assert `artifacts/<session_id>/rejected_auth_callbacks.jsonl`
  has the expected line shape and no secret / body. (T032 writes this file; not yet
  implemented.)
- **C.** **Both** — SC-018 says "0 secrets in artifacts, run report, payloads" so the test
  should grep both surfaces. T013b (the dedicated rejected-auth contract test) already does
  this on JSONL; T013 could focus narrowly on SQLite to avoid duplication.

**Answer: A.** Keep T013 focused on SQLite and query `rejected_auth_callbacks` directly. Assert
that the row shape contains only the approved metadata and that no value includes the signing
secret or callback body bytes. JSONL/artifact scanning belongs to T013b and later artifact-writer
tests, so T013 should not depend on the T032 artifact implementation.

## Q8 — Scope of `test_provider_4xx_does_not_consume_attempt`

"No attempt_count increment" and "no Phone Call activity emitted" — neither is the
transport's responsibility (the transport calls SignalWire's dial endpoint and translates the
response). Where does the test draw its boundary?

- **A.** **Narrow** — the transport test asserts `place_call` raises `ProviderRejectedDialError`
  on a 4xx and never returns a `ProviderCallId`. The "no attempt consumed / no Phone Call
  activity" assertions move to a US3 integration test (T043 already exists for this).
- **B.** **End-to-end** — the contract test reaches into a fake runner + fake Dataverse
  adapter and asserts attempt count + Phone Call activity emission. Bigger test, but matches
  the literal contract wording.

**Answer: A.** Draw the transport boundary narrowly. T013 should assert that `place_call` raises
`ProviderRejectedDialError` on provider 4xx and never returns a `ProviderCallId`. Attempt-count
and Phone Call activity behavior are orchestration/write-back responsibilities and should stay in
the US3 integration test path, including T043.

## Q9 — `test_no_signalwire_specifics_leak` strategy

`tests/contract/test_boundary_isolation.py` does **source-file string scanning** for vendor
leakage. The new no-leak test could do:

- **A.** **Runtime check** — drive a synthetic callback through the adapter and assert the
  emitted `CallEvent` instances contain 0 SignalWire intermediate state names
  (`ringing`, `in_progress`, etc.) in any field including `payload`.
- **B.** **Source-file scan** — extend `test_boundary_isolation.py`'s `_MODULES_UNDER_TEST`
  tuple to include the orchestrator, eligibility, persona, and Dataverse adapter, and assert
  none of the SignalWire intermediate names appear as string literals there.
- **C.** **Both** — runtime check in T013; static check is a one-line append to the existing
  boundary-isolation test.

**Answer: C.** Do both. T013 should runtime-drive a synthetic callback through the adapter and
assert the emitted `CallEvent` contains only normalized event types/fields, with no SignalWire
intermediate state names in `event_type` or `payload`. Also extend the existing boundary-isolation
source scan so orchestrator, eligibility, persona, and Dataverse code remain free of SignalWire
state strings.

## Q10 — Conftest fixtures for `QueueItem` / `DialPlan` / `session_id`

T013 needs valid `QueueItem`, `DialPlan`, and `session_id` instances to call `place_call`.

- **A.** **Fixture file** — add `tests/contract/conftest.py` (or extend root `tests/conftest.py`)
  with `pytest.fixture` factories for `valid_queue_item`, `valid_dial_plan`, `valid_session_id`.
  Reusable by T013b / T014 / T015 / T016 / T068.
- **B.** **Inline construction** — each test constructs its own inputs from `models.QueueItem(...)`
  literals. Simpler now; risks duplication when 5 more contract tests land.
- **C.** **Factory module** — `tests/fixtures/builders.py` with `build_queue_item(**overrides)`
  helpers. Heavier; matches a more mature test stack.

**Answer: A.** Add reusable pytest fixtures, preferably in `tests/contract/conftest.py` so the
scope stays close to the Slice 3 contract tests. Provide `valid_queue_item`, `valid_dial_plan`,
and `valid_session_id` fixtures now; if later tests need heavy override logic, those fixtures can
delegate to builder helpers without forcing T013 to start with a larger factory module.

---

## Ground truth references (so answers can cite line numbers)

| Topic | File | Lines |
|---|---|---|
| `CallEvent` / `MockCallEvent` model | `src/opencloser/models.py` | 235-270, 1103 |
| `ProviderCallId`, `DialPlan` aliases | `src/opencloser/models.py` | 944-945 |
| `RejectedAuthCallback` model | `src/opencloser/models.py` | 964-977 |
| `Slice3RunMode` enum | `src/opencloser/models.py` | 868-879 |
| `QueueStatusUpdateVariant` enum | `src/opencloser/models.py` | 882-893 |
| Existing Slice 3 SQLite tables | `src/opencloser/state/schema.sql` | (3 new tables T005 added) |
| Existing contract-test pattern | `tests/contract/test_boundary_isolation.py` | 1-50 |
| Existing conftest | `tests/conftest.py` | (whole file, 1111 bytes) |
| Contract assertions | `specs/003-real-call-real-crm/contracts/signalwire-transport.md` | 101-114 |
| SignalWire SDK + receiver decision | `specs/003-real-call-real-crm/research.md` | §1 |
| HMAC-SHA256 + audit log decision | `specs/003-real-call-real-crm/research.md` | §2 |
| Timeouts + grace window | `specs/003-real-call-real-crm/research.md` | §7 |
| `signalwire>=2.0,<3.0` dep | `pyproject.toml` | 18 |

---

**Answered 2026-05-25**: Q1 A, Q2 C, Q3 A, Q4 A, Q5 B, Q6 B, Q7 A, Q8 A, Q9 C, Q10 A.

Path: `/workspace/projects/openCloser-worktrees/003-real-call-real-crm/specs/003-real-call-real-crm/t013-clarify-questions.md`
