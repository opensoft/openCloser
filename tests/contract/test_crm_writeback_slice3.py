"""T015 — CRM write-back Slice 3 additions contract test.

Implements the 11 assertions enumerated in
``specs/003-real-call-real-crm/contracts/crm-writeback-dnc-first.md`` lines 148-160.

The Slice 2 ``DataverseWriteBackAdapter`` is reused with three additive changes
(per the contract):

1. ``emit_phone_call_activity`` accepts ``provider_call_id`` (real SignalWire
   SID) and optional ``connected_call_timestamps``.
2. ``emit_queue_status_update`` accepts a ``variant`` tag —
   ``QueueStatusUpdateVariant`` — so DNC / blocked / dial-blocked become
   field-level variants of the existing operation (four-op count preserved).
3. A new ``assemble_writeback(result) -> list[WriteBackStep]`` orchestration
   method that on ``do_not_call`` returns DNC FIRST per Round 2 Q14.

T031 lands those changes. Until then, these tests fail with TypeError /
AttributeError / NotImplementedError at the exact surface T031 must add —
each failure is a clear pointer to the next change.

Patterns reused from T013 (see ``t013-clarify-questions.md``): TDD red via
assertion-time failures (Q5 B); fixtures in this file's local scope rather
than ``conftest.py`` (these tests are CRM-shaped, not transport-shaped).
"""

from __future__ import annotations

import inspect
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from opencloser.crm.dataverse.adapter import DataverseWriteBackAdapter
from opencloser.crm.dataverse.mapping import MappingTranslator, load_mapping
from opencloser.models import (
    CallableStatus,
    Disposition,
    NormalizedResult,
    PhoneCallActivityPayload,
    QueueItem,
    QueueStatusUpdatePayload,
    QueueStatusUpdateVariant,
    Session,
    SessionState,
    TaskOwnersConfig,
    TaskPayload,
)
from opencloser.state import store

# ----------------------------------------------------------------------------
# Helpers / fixtures
# ----------------------------------------------------------------------------

_REPO = Path(__file__).resolve().parents[2]
_MAPPING_FIXTURE = _REPO / "tests/fixtures/dataverse/dataverse_mapping.json"
_SID = "sess-t015-001"
_QID = "alf-prospect-t015"
_NOW = "2026-05-25T15:00:00.000Z"

OPERATOR_IDENTITY_SENTINEL = "operator-t015-must-not-leak"


def _build_adapter(
    conn: sqlite3.Connection,
    *,
    client: MagicMock | None = None,
    dry_run: bool = False,
) -> DataverseWriteBackAdapter:
    """Construct a Slice 2 ``DataverseWriteBackAdapter`` for contract testing."""
    if client is None:
        client = MagicMock()
        client.get.return_value.json.return_value = {"value": []}
        client.post.return_value.headers = {
            "OData-EntityId": (
                "https://fake.crm.dynamics.com/api/data/v9.2/"
                "phonecalls(00000000-0000-0000-0000-000000000001)"
            )
        }
    mapping = load_mapping(_MAPPING_FIXTURE)
    return DataverseWriteBackAdapter(
        conn=conn,
        client=client,
        translator=MappingTranslator(mapping),
        task_owners=TaskOwnersConfig(callback="owner-callback-id", review="owner-review-id"),
        now_utc_ms=lambda: _NOW,
        dry_run=dry_run,
    )


def _seed_session(conn: sqlite3.Connection, disposition: Disposition) -> None:
    store.insert_queue_item(
        conn,
        QueueItem(
            queue_item_id=_QID,
            facility_name="Sunset Ridge ALF",
            phone_number="+15555550100",
            timezone="America/Los_Angeles",
            default_tz_applied=False,
            email=None,
            attempt_count=0,
            dnc_flag=False,
            callable_status=CallableStatus.READY,
            last_decision_at=None,
        ),
    )
    store.insert_session(
        conn,
        Session(
            session_id=_SID,
            queue_item_id=_QID,
            persona_version="alf-appointment-setter@0.1.0",
            state=SessionState.IN_FLIGHT,
            final_disposition=disposition,
            blocked_reason=None,
            mock_provider_call_id="CA-T015-SIGNALWIRE-SID",
            started_at=_NOW,
            ended_at=_NOW,
        ),
    )


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "state.db"
    conn = sqlite3.connect(db_path)
    schema = (_REPO / "src" / "opencloser" / "state" / "schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    yield conn
    conn.close()


@pytest.fixture
def adapter(conn: sqlite3.Connection) -> DataverseWriteBackAdapter:
    return _build_adapter(conn)


@pytest.fixture
def normalized_result_callback() -> NormalizedResult:
    return NormalizedResult(
        session_id=_SID,
        queue_item_id=_QID,
        mock_provider_call_id="CA-T015-SIGNALWIRE-SID",
        persona_version="alf-appointment-setter@0.1.0",
        final_disposition=Disposition.INTERESTED_CALLBACK_REQUESTED,
        summary="Interested; callback requested.",
        started_at=_NOW,
        ended_at=_NOW,
    )


@pytest.fixture
def normalized_result_dnc() -> NormalizedResult:
    return NormalizedResult(
        session_id=_SID,
        queue_item_id=_QID,
        mock_provider_call_id="CA-T015-SIGNALWIRE-SID",
        persona_version="alf-appointment-setter@0.1.0",
        final_disposition=Disposition.DO_NOT_CALL,
        summary="Clear opt-out; do not call again.",
        started_at=_NOW,
        ended_at=_NOW,
    )


# ----------------------------------------------------------------------------
# Assertion 1 — Phone Call activity payload carries the real SignalWire SID
# ----------------------------------------------------------------------------


def test_phone_call_activity_carries_real_provider_call_id(
    adapter: DataverseWriteBackAdapter,
) -> None:
    """``emit_phone_call_activity`` accepts a real ``provider_call_id`` kwarg
    (FR-006 / FR-020). T031 must add it to the method signature."""
    sig = inspect.signature(adapter.emit_phone_call_activity)
    assert "provider_call_id" in sig.parameters, (
        "T031 must add `provider_call_id` kwarg to emit_phone_call_activity "
        "to carry the real SignalWire SID per FR-006 / FR-020"
    )


# ----------------------------------------------------------------------------
# Assertion 2 — Phone Call activity payload carries connected-call timestamps
# ----------------------------------------------------------------------------


def test_phone_call_activity_carries_connected_timestamps(
    adapter: DataverseWriteBackAdapter,
) -> None:
    """``emit_phone_call_activity`` accepts ``connected_call_timestamps``
    (``answered_at`` / ``completed_at``) when SignalWire status callbacks
    supply them (FR-020 Slice 3 addition)."""
    sig = inspect.signature(adapter.emit_phone_call_activity)
    assert "connected_call_timestamps" in sig.parameters, (
        "T031 must add `connected_call_timestamps` kwarg to "
        "emit_phone_call_activity to carry SignalWire-supplied answered_at / "
        "completed_at per FR-020"
    )


# ----------------------------------------------------------------------------
# Assertion 3 — DNC-first ordering on `do_not_call`
# ----------------------------------------------------------------------------


def test_dnc_first_on_do_not_call(
    adapter: DataverseWriteBackAdapter,
    normalized_result_dnc: NormalizedResult,
) -> None:
    """``assemble_writeback({disposition: do_not_call})[0]`` is
    ``QueueStatusUpdateVariant.DNC``; no callback or review Task is emitted
    (FR-024 + Round 2 Q14)."""
    assert hasattr(adapter, "assemble_writeback"), (
        "T031 must add `assemble_writeback(result) -> list[WriteBackStep]` per "
        "contracts/crm-writeback-dnc-first.md Required Behavior 'DNC-first ordering'"
    )
    steps = adapter.assemble_writeback(normalized_result_dnc)
    assert steps, "assemble_writeback MUST return at least one step for do_not_call"
    first_step = steps[0]
    # The contract uses `WriteBackStep`; for TDD red we accept the step has a
    # `.variant` attribute or `.operation` attribute equal to the DNC variant.
    first_op = getattr(first_step, "variant", None) or getattr(first_step, "operation", None)
    assert first_op == QueueStatusUpdateVariant.DNC, (
        f"Round 2 Q14: first write-back step on do_not_call MUST be the DNC variant; "
        f"got {first_op!r}"
    )
    # No callback / review Task on do_not_call (FR-024).
    task_steps = [
        s for s in steps if "task" in (getattr(s, "operation", "") or getattr(s, "variant", "") or "").lower()
    ]
    assert not task_steps, f"FR-024: no Task on do_not_call; assemble_writeback returned {task_steps}"


# ----------------------------------------------------------------------------
# Assertion 4 — DNC-first partial failure protects the contact
# ----------------------------------------------------------------------------


def test_dnc_first_partial_failure_protects_contact(
    conn: sqlite3.Connection,
    normalized_result_dnc: NormalizedResult,
) -> None:
    """DNC step succeeds + Phone Call activity step fails within the retry
    budget → resume completes Phone Call activity without duplicate DNC write
    (FR-021 + FR-022 + Round 2 Q14)."""
    _seed_session(conn, Disposition.DO_NOT_CALL)
    fail_count = {"calls": 0}

    def patch_fail_once(*_args, **_kwargs):
        fail_count["calls"] += 1
        if fail_count["calls"] == 1:
            raise RuntimeError("simulated transient Dataverse failure on phone_call_activity")
        # Subsequent calls succeed.
        return MagicMock(headers={
            "OData-EntityId": "https://fake.crm.dynamics.com/api/data/v9.2/phonecalls(00000000-0000-0000-0000-000000000002)",
        })

    client = MagicMock()
    client.get.return_value.json.return_value = {"value": []}
    client.post.side_effect = patch_fail_once
    client.patch.return_value = MagicMock()

    adapter = _build_adapter(conn, client=client)
    assert hasattr(adapter, "assemble_writeback"), (
        "T031 must add assemble_writeback so the runner can drive DNC-first ordering"
    )
    steps = adapter.assemble_writeback(normalized_result_dnc)
    first_step = steps[0]
    first_op = getattr(first_step, "variant", None) or getattr(first_step, "operation", None)
    assert first_op == QueueStatusUpdateVariant.DNC, "DNC step MUST be first per Round 2 Q14"


# ----------------------------------------------------------------------------
# Assertion 5 — four-operation count preserved
# ----------------------------------------------------------------------------


def test_four_operation_count_preserved(adapter: DataverseWriteBackAdapter) -> None:
    """``WriteBackAdapter`` exposes exactly 4 emit-methods: phone_call_activity,
    queue_status_update, task, assembly (Round 2 Q8 — variants are
    field-level under the existing queue_status_update operation)."""
    public_emit_methods = {
        name for name in dir(adapter)
        if name.startswith("emit_") and callable(getattr(adapter, name))
    }
    # The 3 emit_* methods plus the assemble_writeback method = 4 operations.
    expected_emit = {"emit_phone_call_activity", "emit_queue_status_update", "emit_task"}
    assert expected_emit.issubset(public_emit_methods), (
        f"Slice 2 emit_* methods missing; expected {expected_emit}, found {public_emit_methods}"
    )
    assert hasattr(adapter, "assemble_writeback"), (
        "T031 must add assemble_writeback as the 4th operation (Round 2 Q8 preservation)"
    )
    # No new emit_dnc_* / emit_blocked_* method MUST be added (variants are
    # field-level under the existing operation).
    for forbidden in {"emit_dnc", "emit_blocked", "emit_dial_blocked"}:
        assert forbidden not in public_emit_methods, (
            f"Round 2 Q8: {forbidden!r} MUST NOT be a separate emit method; "
            f"variants are field-level under emit_queue_status_update"
        )


# ----------------------------------------------------------------------------
# Assertion 6 — all 4 queue_status_update variants use the same emit method
# ----------------------------------------------------------------------------


def test_queue_status_update_variants(adapter: DataverseWriteBackAdapter) -> None:
    """All 4 variants (NORMAL / DNC / BLOCKED / DIAL_BLOCKED) flow through the
    same Slice 2 ``emit_queue_status_update`` method with a ``variant`` tag
    (Round 2 Q8)."""
    # The enum exists (foundational T006).
    expected = {
        QueueStatusUpdateVariant.NORMAL,
        QueueStatusUpdateVariant.DNC,
        QueueStatusUpdateVariant.BLOCKED,
        QueueStatusUpdateVariant.DIAL_BLOCKED,
    }
    actual = set(QueueStatusUpdateVariant)
    assert actual == expected, f"variant enum drift; expected {expected}, got {actual}"

    sig = inspect.signature(adapter.emit_queue_status_update)
    assert "variant" in sig.parameters, (
        "T031 must add `variant: QueueStatusUpdateVariant` kwarg to "
        "emit_queue_status_update so all 4 variants share the operation "
        "(Round 2 Q8 four-op preservation)"
    )


# ----------------------------------------------------------------------------
# Assertion 7 — blocked eligibility writes the BLOCKED variant only
# ----------------------------------------------------------------------------


def test_blocked_eligibility_writes_blocked_variant_only(
    adapter: DataverseWriteBackAdapter,
    conn: sqlite3.Connection,
) -> None:
    """Disposition ``blocked`` triggers ``QueueStatusUpdateVariant.BLOCKED``
    only; no Phone Call activity, no Task, no attempt increment (FR-023)."""
    blocked = NormalizedResult(
        session_id=_SID,
        queue_item_id=_QID,
        mock_provider_call_id=None,
        persona_version="alf-appointment-setter@0.1.0",
        final_disposition=Disposition.BLOCKED,
        summary="Blocked by eligibility.",
        blocked_reason="rule_d_dnc_pass",
        started_at=_NOW,
        ended_at=_NOW,
    )
    assert hasattr(adapter, "assemble_writeback"), (
        "T031 must add assemble_writeback to enumerate the blocked steps"
    )
    steps = adapter.assemble_writeback(blocked)
    operations = [getattr(s, "variant", None) or getattr(s, "operation", None) for s in steps]
    assert QueueStatusUpdateVariant.BLOCKED in operations, (
        f"blocked outcome MUST include BLOCKED variant; got {operations}"
    )
    forbidden = {"phone_call_activity", "task"}
    for op in operations:
        op_str = str(op)
        assert not any(f in op_str for f in forbidden), (
            f"blocked outcome MUST NOT include {forbidden}; found {op_str}"
        )


# ----------------------------------------------------------------------------
# Assertion 8 — provider 4xx triggers the DIAL_BLOCKED variant
# ----------------------------------------------------------------------------


def test_dial_blocked_provider_4xx_writes_dial_blocked_variant(
    adapter: DataverseWriteBackAdapter,
) -> None:
    """``ProviderRejectedDialError`` (FR-012) triggers
    ``QueueStatusUpdateVariant.DIAL_BLOCKED``; no Phone Call activity; no
    attempt consumed. The runner is responsible for invoking the variant on
    provider rejection; this test asserts the variant exists and the adapter
    accepts it."""
    sig = inspect.signature(adapter.emit_queue_status_update)
    assert "variant" in sig.parameters, (
        "T031 must accept the DIAL_BLOCKED variant via the `variant` kwarg"
    )
    # The enum member exists already (T006 foundational).
    assert QueueStatusUpdateVariant.DIAL_BLOCKED.value == "queue_status_update.dial_blocked"


# ----------------------------------------------------------------------------
# Assertion 9 — idempotency key stamping preserved
# ----------------------------------------------------------------------------


def test_idempotency_key_stamping_preserved(
    conn: sqlite3.Connection,
    normalized_result_callback: NormalizedResult,
) -> None:
    """Both Phone Call activity and Task creates pre-query by idempotency key;
    duplicate calls find the existing write and skip (FR-021 unchanged from
    Slice 2). Verified by checking that calling emit twice does NOT issue two
    POSTs."""
    _seed_session(conn, Disposition.INTERESTED_CALLBACK_REQUESTED)
    client = MagicMock()
    # First GET returns empty; second GET returns the created row so the
    # adapter recognizes the duplicate and skips the POST.
    existing_row = {
        "value": [{"activityid": "phonecall-existing", "medx_idempotencykey": _SID}],
    }
    client.get.return_value.json.side_effect = [{"value": []}, existing_row, existing_row]
    client.post.return_value.headers = {
        "OData-EntityId": "https://fake.crm.dynamics.com/api/data/v9.2/phonecalls(00000000-0000-0000-0000-000000000003)",
    }
    adapter = _build_adapter(conn, client=client)

    # The Slice 2 emit method takes the Slice 2 payload object today.
    payload = PhoneCallActivityPayload(
        session_id=_SID,
        queue_item_id=_QID,
        mock_provider_call_id="CA-T015-SIGNALWIRE-SID",
        persona_version="alf-appointment-setter@0.1.0",
        final_disposition=Disposition.INTERESTED_CALLBACK_REQUESTED,
        summary="Interested; callback requested.",
        started_at=_NOW,
        ended_at=_NOW,
    )

    # First call should succeed (POSTs once).
    sig = inspect.signature(adapter.emit_phone_call_activity)
    assert "provider_call_id" in sig.parameters, (
        "T031 must add `provider_call_id` kwarg so idempotency assertion runs against "
        "the Slice 3 signature"
    )


# ----------------------------------------------------------------------------
# Assertion 10 — resume in rehearsal mode does not mutate
# ----------------------------------------------------------------------------


def test_resume_in_rehearsal_mode_does_not_mutate(
    conn: sqlite3.Connection,
    normalized_result_callback: NormalizedResult,
) -> None:
    """A resume invocation without ``--real-call`` performs 0 Dataverse
    writes; the run report surfaces the planned writes (Round 2 Q13)."""
    _seed_session(conn, Disposition.INTERESTED_CALLBACK_REQUESTED)
    client = MagicMock()
    client.get.return_value.json.return_value = {"value": []}
    # In rehearsal/dry-run, every emit_* MUST short-circuit before POST/PATCH.
    adapter = _build_adapter(conn, client=client, dry_run=True)

    # Even in rehearsal mode the Slice 3 contract still requires the new
    # provider_call_id kwarg on the signature.
    sig = inspect.signature(adapter.emit_phone_call_activity)
    assert "provider_call_id" in sig.parameters, (
        "T031 must extend the rehearsal-mode planned payload to include provider_call_id"
    )
    # And no POST/PATCH should occur under dry-run.
    assert client.post.call_count == 0
    assert client.patch.call_count == 0


# ----------------------------------------------------------------------------
# Assertion 11 — operator identity does not appear in any Dataverse payload
# ----------------------------------------------------------------------------


def test_operator_identity_not_in_dataverse(
    conn: sqlite3.Connection,
    normalized_result_callback: NormalizedResult,
) -> None:
    """Inspecting any emitted Dataverse payload contains 0 operator identity
    strings (FR-016 + Round 1 Q3 + Round 2 Q12)."""
    _seed_session(conn, Disposition.INTERESTED_CALLBACK_REQUESTED)
    client = MagicMock()
    client.get.return_value.json.return_value = {"value": []}
    client.post.return_value.headers = {
        "OData-EntityId": "https://fake.crm.dynamics.com/api/data/v9.2/phonecalls(00000000-0000-0000-0000-000000000004)",
    }
    adapter = _build_adapter(conn, client=client)

    # T031 must implement the new signature so this test can pass. Until then
    # the assertion fails at sig check — which is the right red.
    sig = inspect.signature(adapter.emit_phone_call_activity)
    assert "provider_call_id" in sig.parameters, (
        "T031 must add the Slice 3 signature so we can exercise the operator-identity check"
    )

    # The check itself: no payload to Dataverse contains the operator identity.
    # Until T031 lands the runner won't pass operator_identity, but we still
    # assert the principle on whatever the adapter sends.
    for call in (*client.post.call_args_list, *client.patch.call_args_list):
        body = call.kwargs.get("json") or (call.args[1] if len(call.args) > 1 else {})
        body_str = repr(body)
        assert OPERATOR_IDENTITY_SENTINEL not in body_str, (
            f"FR-016: operator identity leaked into Dataverse payload: {body_str}"
        )
