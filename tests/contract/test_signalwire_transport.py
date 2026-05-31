"""T013 — SignalWire transport contract test.

Implements the 10 assertions enumerated in
``specs/003-real-call-real-crm/contracts/signalwire-transport.md`` lines 101-114.

Design decisions (recorded in
``specs/003-real-call-real-crm/t013-clarify-questions.md``):

- Q1 (A) — ``MockCallEvent`` carries 3 optional bool flags
  (``is_duplicate``, ``out_of_order``, ``late_after_finalization``).
- Q2 (C) — dedup state is mirrored to SQLite ``signalwire_callbacks`` for
  audit; T013 pins the SQLite surface.
- Q3 (A) — callbacks are fed via ``await adapter.ingest_callback(...)``.
- Q4 (A) — ``SignalWireClient`` is constructor-injected; tests use
  ``FakeSignalWireClient``.
- Q5 (B) — TDD red is assertion-time: the stubs in
  ``src/opencloser/transport/signalwire/`` raise ``NotImplementedError`` so
  each ``pytest.raises(<spec-mandated exception>)`` fails with a clear
  "expected X, got NotImplementedError" until T022-T026 land.
- Q6 (B) — strict ``pytest-asyncio``; each async test is explicitly marked.
- Q7 (A) — audit-log redaction asserted against the SQLite
  ``rejected_auth_callbacks`` table (T013b covers the JSONL surface).
- Q8 (A) — narrow boundary; "no attempt consumed / no Phone Call activity"
  assertions live in the US3 integration test (T043).
- Q9 (C) — runtime check here; ``test_boundary_isolation.py`` extension
  covers the source-file string scan.
- Q10 (A) — fixtures live in ``tests/contract/conftest.py``.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from opencloser.models import CallEvent, QueueItem
from opencloser.transport.signalwire.adapter import SignalWireTransport
from opencloser.transport.signalwire.errors import (
    ProviderRejectedDialError,
    RealDialPhoneValidationError,
    SignatureVerificationError,
)
from tests.fixtures.signalwire import (
    CallCreated,
    CallRejected,
    FakeSignalWireClient,
)

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]

# SignalWire intermediate state names that MUST NOT leak past the transport
# boundary (FR-005, SC-015). Used by ``test_no_signalwire_specifics_leak``.
_SIGNALWIRE_INTERMEDIATE_STATES: frozenset[str] = frozenset({
    "ringing",
    "answered",
    "in_progress",
    "in-progress",
    "busy",
    "canceled",
    "cancelled",
})


def _build_callback_headers(*, signature: str = "deadbeef", event_id: str = "EV-1") -> dict[str, str]:
    """Build a minimal SignalWire-shaped callback header set."""
    return {
        "X-SignalWire-Signature": signature,
        "X-SignalWire-Event-Id": event_id,
        "Content-Type": "application/json",
    }


def _build_callback_body(*, call_status: str, provider_call_id: str = "CA-1") -> bytes:
    """Build a minimal SignalWire-shaped callback body."""
    payload = {
        "CallSid": provider_call_id,
        "CallStatus": call_status,
        "AccountSid": "AC-fake",
    }
    return json.dumps(payload).encode("utf-8")


def _open_state_db() -> sqlite3.Connection:
    """Open the SQLite state store the audit-log tests inspect.

    Path mirrors ``src/opencloser/state/store.py`` default. Tests run in a
    repo-local working directory so the default location is fine.
    """
    db_path = _REPO_ROOT / "state.db"
    return sqlite3.connect(db_path)


# ----------------------------------------------------------------------------
# Assertion 1 — place_call returns a non-empty ProviderCallId
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_place_call_returns_provider_call_id(
    signalwire_transport: SignalWireTransport,
    fake_signalwire_client: FakeSignalWireClient,
    valid_queue_item: QueueItem,
    valid_dial_plan: str,
    valid_session_id: str,
) -> None:
    """`place_call` returns the SignalWire-assigned call SID for a valid input."""
    fake_signalwire_client.queue_response(CallCreated(sid="CA-T013-001"))

    provider_call_id = await signalwire_transport.place_call(
        valid_queue_item,
        valid_dial_plan,
        session_id=valid_session_id,
    )

    assert isinstance(provider_call_id, str)
    assert provider_call_id, "place_call returned an empty ProviderCallId"
    assert fake_signalwire_client.calls_placed == 1


# ----------------------------------------------------------------------------
# Assertion 2 — event_stream normalizes intermediate states
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_stream_normalizes_intermediate_states(
    signalwire_transport: SignalWireTransport,
    valid_session_id: str,
) -> None:
    """``ringing → in_progress → answered → completed`` produces exactly one
    ``connected`` event followed by one ``completed`` event (FR-005)."""
    provider_call_id = "CA-T013-002"

    for idx, status in enumerate(["ringing", "in_progress", "answered", "completed"]):
        await signalwire_transport.ingest_callback(
            session_id=valid_session_id,
            headers=_build_callback_headers(event_id=f"EV-{idx}"),
            body=_build_callback_body(call_status=status, provider_call_id=provider_call_id),
        )

    emitted: list[CallEvent] = []
    async for event in signalwire_transport.event_stream(provider_call_id):
        emitted.append(event)

    event_types = [e.event_type for e in emitted]
    assert event_types == ["connected", "completed"], (
        f"intermediate states leaked; expected [connected, completed], got {event_types}"
    )


# ----------------------------------------------------------------------------
# Assertion 3 — duplicate callbacks marked is_duplicate=True
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_stream_dedups_duplicate_callbacks(
    signalwire_transport: SignalWireTransport,
    valid_session_id: str,
) -> None:
    """Same ``(session_id, provider_event_id)`` twice yields a single event
    with ``is_duplicate=True`` on the second delivery (FR-007, FR-021)."""
    provider_call_id = "CA-T013-003"
    duplicated_event_id = "EV-DUP"

    for _ in range(2):
        await signalwire_transport.ingest_callback(
            session_id=valid_session_id,
            headers=_build_callback_headers(event_id=duplicated_event_id),
            body=_build_callback_body(call_status="completed", provider_call_id=provider_call_id),
        )

    emitted: list[CallEvent] = []
    async for event in signalwire_transport.event_stream(provider_call_id):
        emitted.append(event)

    assert len(emitted) == 2, f"expected 2 emitted events (one + one duplicate), got {len(emitted)}"
    assert emitted[0].is_duplicate is False, "first delivery should not be marked duplicate"
    assert emitted[1].is_duplicate is True, "second delivery MUST be marked is_duplicate=True"


# ----------------------------------------------------------------------------
# Assertion 4 — out-of-order delivery flagged
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_stream_marks_out_of_order(
    signalwire_transport: SignalWireTransport,
    valid_session_id: str,
) -> None:
    """``completed`` arriving before ``answered`` produces a coherent
    normalized stream; the late event is marked ``out_of_order=True``
    (FR-005, edge case "out of order")."""
    provider_call_id = "CA-T013-004"

    # 1. completed arrives first
    await signalwire_transport.ingest_callback(
        session_id=valid_session_id,
        headers=_build_callback_headers(event_id="EV-COMPLETED-FIRST"),
        body=_build_callback_body(call_status="completed", provider_call_id=provider_call_id),
    )
    # 2. answered arrives after — out of order
    await signalwire_transport.ingest_callback(
        session_id=valid_session_id,
        headers=_build_callback_headers(event_id="EV-ANSWERED-LATE"),
        body=_build_callback_body(call_status="answered", provider_call_id=provider_call_id),
    )

    emitted: list[CallEvent] = []
    async for event in signalwire_transport.event_stream(provider_call_id):
        emitted.append(event)

    out_of_order_flags = [e.out_of_order for e in emitted]
    assert any(out_of_order_flags), "at least one event must be marked out_of_order=True"


# ----------------------------------------------------------------------------
# Assertion 5 — late-after-finalization routed to ConflictingEventAuditLog
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_stream_marks_late_after_finalization(
    signalwire_transport: SignalWireTransport,
    valid_session_id: str,
) -> None:
    """A callback arriving after the session is finalized is marked
    ``late_after_finalization=True`` and routed to the conflicting-events
    audit log (FR-027). The finalized disposition is unchanged."""
    provider_call_id = "CA-T013-005"

    # Drive a terminal event and finalize.
    await signalwire_transport.ingest_callback(
        session_id=valid_session_id,
        headers=_build_callback_headers(event_id="EV-COMPLETED"),
        body=_build_callback_body(call_status="completed", provider_call_id=provider_call_id),
    )
    async for _ in signalwire_transport.event_stream(provider_call_id):
        pass  # drain to finalization

    # Now a stray callback arrives after finalization.
    await signalwire_transport.ingest_callback(
        session_id=valid_session_id,
        headers=_build_callback_headers(event_id="EV-LATE"),
        body=_build_callback_body(call_status="failed", provider_call_id=provider_call_id),
    )

    # The late event MUST land in the conflicting-events audit log.
    conflicting_log = _REPO_ROOT / "artifacts" / valid_session_id / "conflicting_callbacks_audit.jsonl"
    assert conflicting_log.exists(), (
        f"expected conflicting-events audit log at {conflicting_log}; "
        "FR-027 requires late-after-finalization callbacks to be recorded there"
    )
    rows = [json.loads(line) for line in conflicting_log.read_text().splitlines() if line.strip()]
    assert any(r.get("provider_event_id") == "EV-LATE" for r in rows), (
        "late callback EV-LATE missing from conflicting-events audit log"
    )


# ----------------------------------------------------------------------------
# Assertion 6 — bad signature → 401 + RejectedAuthCallbackLog + no hand-off
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_signature_verification_rejects_bad_signature(
    signalwire_transport: SignalWireTransport,
    valid_session_id: str,
) -> None:
    """A forged callback (invalid HMAC) raises ``SignatureVerificationError``
    with HTTP 401, is recorded in ``RejectedAuthCallbackLog``, and is NOT
    handed off to the orchestrator (FR-008, Round 2 Q9)."""
    with pytest.raises(SignatureVerificationError) as exc_info:
        await signalwire_transport.ingest_callback(
            session_id=valid_session_id,
            headers=_build_callback_headers(signature="forged-not-a-real-hmac"),
            body=_build_callback_body(call_status="completed"),
        )

    assert exc_info.value.http_status == 401, "rejected-auth response MUST be HTTP 401"

    with _open_state_db() as conn:
        rows = conn.execute(
            "SELECT received_at, session_id, http_status FROM rejected_auth_callbacks "
            "WHERE session_id = ?",
            (valid_session_id,),
        ).fetchall()
    assert len(rows) >= 1, "rejected-auth callback MUST be recorded in rejected_auth_callbacks"
    assert all(row[2] == 401 for row in rows), "all rejected-auth rows MUST have http_status=401"


# ----------------------------------------------------------------------------
# Assertion 7 — rejected-auth audit log carries no secret, no body
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_signature_verification_does_not_log_secret_or_body(
    signalwire_transport: SignalWireTransport,
    signing_secret: str,
    valid_session_id: str,
) -> None:
    """The ``rejected_auth_callbacks`` row contains only
    ``(received_at, session_id, source_metadata, http_status)`` and MUST NOT
    carry the signing secret or the callback body (FR-008, FR-035, SC-018,
    Round 2 Q9)."""
    forged_body = _build_callback_body(call_status="completed")
    sensitive_marker = "T013-SECRET-MARKER-must-not-appear-in-audit"
    try:
        await signalwire_transport.ingest_callback(
            session_id=valid_session_id,
            headers={
                **_build_callback_headers(signature="forged"),
                "X-SignalWire-Secret-Echo": sensitive_marker,  # would be sensitive if leaked
            },
            body=forged_body,
        )
    except SignatureVerificationError:
        pass

    with _open_state_db() as conn:
        # The expected column set per FR-008 Round 2 Q9.
        expected_columns = {"received_at", "session_id", "source_metadata_json", "http_status"}
        actual_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(rejected_auth_callbacks)").fetchall()
        }
        assert expected_columns.issubset(actual_columns), (
            f"rejected_auth_callbacks must contain {expected_columns}, has {actual_columns}"
        )

        rows = conn.execute("SELECT * FROM rejected_auth_callbacks").fetchall()
        flat_blob = json.dumps(rows)
        assert signing_secret not in flat_blob, "signing secret leaked into audit row"
        assert forged_body.decode("utf-8") not in flat_blob, "callback body leaked into audit row"
        assert sensitive_marker not in flat_blob, "sensitive header value leaked into audit row"


# ----------------------------------------------------------------------------
# Assertion 8 — non-E.164 destination blocks before dial
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e164_validation_blocks_before_dial(
    signalwire_transport: SignalWireTransport,
    fake_signalwire_client: FakeSignalWireClient,
    invalid_phone_queue_item: QueueItem,
    valid_dial_plan: str,
    valid_session_id: str,
) -> None:
    """A missing / non-E.164 destination phone raises
    ``RealDialPhoneValidationError`` BEFORE ``create_call`` is invoked
    (FR-010)."""
    with pytest.raises(RealDialPhoneValidationError):
        await signalwire_transport.place_call(
            invalid_phone_queue_item,
            valid_dial_plan,
            session_id=valid_session_id,
        )

    assert fake_signalwire_client.calls_placed == 0, (
        "FR-010: SignalWire.create_call MUST NOT be invoked when destination phone is invalid"
    )


# ----------------------------------------------------------------------------
# Assertion 9 — provider 4xx surfaces as ProviderRejectedDialError
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provider_4xx_does_not_consume_attempt(
    signalwire_transport: SignalWireTransport,
    fake_signalwire_client: FakeSignalWireClient,
    valid_queue_item: QueueItem,
    valid_dial_plan: str,
    valid_session_id: str,
) -> None:
    """SignalWire 4xx before placement raises ``ProviderRejectedDialError``;
    no ``ProviderCallId`` is returned (FR-012). Per Q8 the "no attempt
    consumed / no Phone Call activity" assertions live in the US3 integration
    test T043; this contract test stays narrow to the transport boundary."""
    fake_signalwire_client.queue_response(
        CallRejected(http_status=400, provider_message="bad number"),
    )

    with pytest.raises(ProviderRejectedDialError) as exc_info:
        await signalwire_transport.place_call(
            valid_queue_item,
            valid_dial_plan,
            session_id=valid_session_id,
        )

    assert 400 <= exc_info.value.http_status < 500, "ProviderRejectedDialError must carry a 4xx code"
    assert fake_signalwire_client.calls_placed == 0, (
        "no successful placed call when SignalWire returns 4xx pre-placement"
    )


# ----------------------------------------------------------------------------
# Assertion 10 — no SignalWire specifics leak in the emitted CallEvent stream
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_signalwire_specifics_leak(
    signalwire_transport: SignalWireTransport,
    valid_session_id: str,
) -> None:
    """The ``CallEvent`` instances the orchestrator consumes contain 0
    SignalWire intermediate state names (SC-015). Runtime check only — the
    source-file string scan lives in ``test_boundary_isolation.py``."""
    provider_call_id = "CA-T013-010"

    for status in ["ringing", "in_progress", "answered", "completed"]:
        await signalwire_transport.ingest_callback(
            session_id=valid_session_id,
            headers=_build_callback_headers(event_id=f"EV-{status}"),
            body=_build_callback_body(call_status=status, provider_call_id=provider_call_id),
        )

    emitted: list[CallEvent] = []
    async for event in signalwire_transport.event_stream(provider_call_id):
        emitted.append(event)

    forbidden_found: list[str] = []
    for event in emitted:
        # event_type MUST be a normalized name; payload (if present) MUST NOT
        # carry intermediate state strings.
        if str(event.event_type) in _SIGNALWIRE_INTERMEDIATE_STATES:
            forbidden_found.append(f"event.event_type={event.event_type}")
        flat_payload = json.dumps(event.payload, default=str).lower()
        for forbidden in _SIGNALWIRE_INTERMEDIATE_STATES:
            if forbidden in flat_payload:
                forbidden_found.append(f"payload contains {forbidden!r}: {flat_payload}")

    assert not forbidden_found, (
        f"SignalWire intermediate state names leaked into normalized CallEvent stream: "
        f"{forbidden_found}"
    )
