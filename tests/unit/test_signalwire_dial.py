"""T024 — unit tests for SignalWire outbound dial (dial.py).

Covers FR-010 (E.164 pre-dial validation) and FR-012 (provider 4xx) at the
``place_outbound_call`` boundary using the injected ``FakeSignalWireClient``,
plus the ``is_e164`` gate and the opaque SWML dial-plan builder. Mirrors the
focused-unit-test approach of T022/T023.
"""

from __future__ import annotations

import json

import pytest

from opencloser.models import CallableStatus, QueueItem
from opencloser.transport.signalwire.dial import (
    build_swml_dial_plan,
    is_e164,
    place_outbound_call,
)
from opencloser.transport.signalwire.errors import (
    ProviderRejectedDialError,
    RealDialPhoneValidationError,
)
from tests.fixtures.signalwire import CallCreated, CallRejected, FakeSignalWireClient

_DIAL_PLAN = '<placeholder-swml>'


def _queue_item(phone: str | None) -> QueueItem:
    return QueueItem(
        queue_item_id="alf-prospect-t024",
        facility_name="Sunset Ridge ALF",
        phone_number=phone,
        timezone="America/Los_Angeles",
        default_tz_applied=False,
        email=None,
        attempt_count=0,
        dnc_flag=False,
        callable_status=CallableStatus.READY,
        last_decision_at=None,
    )


# ---------------------------------------------------------------------------
# is_e164
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phone,expected",
    [
        ("+15555550100", True),
        ("+447911123456", True),
        ("+1", False),            # too short (needs >= 2 digits)
        ("+05555550100", False),  # leading zero after +
        ("5555550100", False),    # missing +
        ("555-555-0100", False),  # separators
        ("", False),
        (None, False),
    ],
)
def test_is_e164(phone: str | None, expected: bool) -> None:
    assert is_e164(phone) is expected


# ---------------------------------------------------------------------------
# place_outbound_call — happy path
# ---------------------------------------------------------------------------


def test_place_outbound_call_returns_sid() -> None:
    client = FakeSignalWireClient()
    client.queue_response(CallCreated(sid="CA-T024-001"))

    sid = place_outbound_call(
        client=client,
        queue_item=_queue_item("+15555550100"),
        dial_plan=_DIAL_PLAN,
        source_caller_id="+15555550199",
    )

    assert sid == "CA-T024-001"
    assert client.calls_placed == 1
    placed = client.placed_calls[0]
    assert placed.destination == "+15555550100"
    assert placed.source == "+15555550199"


# ---------------------------------------------------------------------------
# place_outbound_call — FR-010: invalid phone blocks BEFORE create_call
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_phone", [None, "", "5555550100", "+1"])
def test_place_outbound_call_blocks_invalid_phone_before_dial(bad_phone: str | None) -> None:
    client = FakeSignalWireClient()
    with pytest.raises(RealDialPhoneValidationError):
        place_outbound_call(
            client=client,
            queue_item=_queue_item(bad_phone),
            dial_plan=_DIAL_PLAN,
            source_caller_id="+15555550199",
        )
    assert client.calls_placed == 0, "FR-010: create_call MUST NOT run on invalid destination"


# ---------------------------------------------------------------------------
# place_outbound_call — FR-012: provider 4xx surfaces as ProviderRejectedDialError
# ---------------------------------------------------------------------------


def test_place_outbound_call_provider_4xx_raises() -> None:
    client = FakeSignalWireClient()
    client.queue_response(CallRejected(http_status=400, provider_message="bad number"))

    with pytest.raises(ProviderRejectedDialError) as exc_info:
        place_outbound_call(
            client=client,
            queue_item=_queue_item("+15555550100"),
            dial_plan=_DIAL_PLAN,
            source_caller_id="+15555550199",
        )
    assert 400 <= exc_info.value.http_status < 500
    assert client.calls_placed == 0


# ---------------------------------------------------------------------------
# build_swml_dial_plan
# ---------------------------------------------------------------------------


def test_build_swml_dial_plan_is_opaque_serialized_string() -> None:
    plan = build_swml_dial_plan(destination="+15555550100", source_caller_id="+15555550199")
    assert isinstance(plan, str) and plan
    # It round-trips as JSON and carries the destination, but callers treat it as
    # opaque — this test only confirms it is a well-formed, deterministic string.
    parsed = json.loads(plan)
    assert parsed["sections"]["main"][0]["connect"]["to"] == "+15555550100"
    # Deterministic (sorted keys) so the same inputs yield the same plan.
    assert build_swml_dial_plan(destination="+15555550100", source_caller_id="+15555550199") == plan


def test_build_swml_dial_plan_includes_status_callback_when_given() -> None:
    plan = build_swml_dial_plan(
        destination="+15555550100",
        source_caller_id="+15555550199",
        status_callback_url="https://example.test/sw/status/sess-1",
    )
    assert "https://example.test/sw/status/sess-1" in plan
