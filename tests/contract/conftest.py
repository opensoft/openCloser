"""Shared fixtures for Slice 3 contract tests (T013 / T013b / T014–T016 / T068).

Per ``specs/003-real-call-real-crm/t013-clarify-questions.md`` Q10: scope
fixtures close to the contract tests rather than to a heavier
``tests/fixtures/builders.py`` module. If later tests need richer override
shapes these can delegate without forcing T013 to start with that surface.
"""

from __future__ import annotations

import pytest

from opencloser.models import CallableStatus, QueueItem
from tests.fixtures.signalwire import FakeSignalWireClient


@pytest.fixture
def valid_session_id() -> str:
    """A deterministic session id usable across contract tests."""
    return "sess-t013-0001"


@pytest.fixture
def valid_queue_item() -> QueueItem:
    """A ``ready`` ALF queue item with a valid E.164 destination phone."""
    return QueueItem(
        queue_item_id="alf-prospect-t013",
        facility_name="Sunset Ridge ALF",
        phone_number="+15555550100",
        timezone="America/Los_Angeles",
        default_tz_applied=False,
        email=None,
        attempt_count=0,
        dnc_flag=False,
        callable_status=CallableStatus.READY,
        last_decision_at=None,
    )


@pytest.fixture
def invalid_phone_queue_item() -> QueueItem:
    """A queue item with a missing destination phone — exercises FR-010."""
    return QueueItem(
        queue_item_id="alf-prospect-t013-no-phone",
        facility_name="Sunset Ridge ALF",
        phone_number=None,
        timezone="America/Los_Angeles",
        default_tz_applied=False,
        email=None,
        attempt_count=0,
        dnc_flag=False,
        callable_status=CallableStatus.READY,
        last_decision_at=None,
    )


@pytest.fixture
def valid_dial_plan() -> str:
    """A placeholder SWML dial plan; the FakeSignalWireClient does not parse it."""
    return "<Response><Dial><Number>+15555550199</Number></Dial></Response>"


@pytest.fixture
def fake_signalwire_client() -> FakeSignalWireClient:
    """A fresh ``FakeSignalWireClient`` with no queued responses (default = success)."""
    return FakeSignalWireClient()


@pytest.fixture
def signing_secret() -> str:
    """A deterministic fake signing secret. Tests that check the audit log
    redaction (T013 Q7) assert this string does NOT appear in any persisted row."""
    return "T013-FAKE-SIGNING-SECRET-not-a-real-key"


@pytest.fixture
def signalwire_transport(
    fake_signalwire_client: FakeSignalWireClient,
    signing_secret: str,
):
    """A ``SignalWireTransport`` instance wired to the fake client.

    Returned untyped so that this fixture does not couple test collection to
    a fully-implemented adapter — the stubs raise ``NotImplementedError`` at
    method call time per Q5 (assertion-time TDD red).
    """
    from opencloser.transport.signalwire.adapter import SignalWireTransport

    return SignalWireTransport(
        client=fake_signalwire_client,
        source_caller_id="+15555550100",
        signing_secret=signing_secret,
    )
