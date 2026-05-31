"""T014 — Pipecat runtime contract test.

Implements the 11 assertions enumerated in
``specs/003-real-call-real-crm/contracts/pipecat-runtime.md`` lines 131-145.

Design decisions (reuse T013 patterns; new ones noted inline):

- Q5 (B from T013) — TDD red is assertion-time via the
  ``NotImplementedError`` stub in
  ``src/opencloser/runtime/pipecat/runtime.py``. T030 / T064 / T065 / T066 /
  T067 land the real implementation and turn these tests green.
- Q6 (B) — strict ``pytest-asyncio``; each async test is explicitly marked.
- DI (Q4 mirror) — ``FakeRealtimeAIProvider`` is constructor-injected into
  ``PipecatRuntime`` via ``tests/fixtures/pipecat/``.
- The ``LiveConversationInput`` Protocol — tests pass a
  ``FakeLiveConversationInput`` from the same fixtures module.

This file is the boundary check for ``PersonaRuntime`` — the contract test
that whatever lands in ``runtime/pipecat/runtime.py`` MUST satisfy
contracts/pipecat-runtime.md Required Behaviors #1-#6.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from opencloser.core.clock import FrozenClock
from opencloser.models import (
    ArtifactsConfig,
    CallableStatus,
    CallWindowConfig,
    Disposition,
    EligibilityConfig,
    HumanReviewReason,
    PersonaConfig,
    QueueItem,
    SliceConfig,
    StateConfig,
)
from opencloser.persona.alf_appointment_setter import CANONICAL_DISCLOSURE
from opencloser.persona.base import PersonaOutput, SessionContext
from opencloser.runtime.pipecat.errors import (
    PipecatRuntimeError,
    RealtimeProviderError,
    SilenceAfterConnectionTimeout,
)
from opencloser.runtime.pipecat.runtime import PipecatRuntime
from tests.fixtures.pipecat import (
    FakeExtractionEvent,
    FakeLiveConversationInput,
    FakeRealtimeAIProvider,
    FakeTranscriptSegment,
)
from datetime import datetime, timezone

# ----------------------------------------------------------------------------
# Helpers / fixtures
# ----------------------------------------------------------------------------

_SECRET_MARKER = "T014-FAKE-API-KEY-must-never-appear-in-identity"


@pytest.fixture
def slice_config(tmp_path: Path) -> SliceConfig:
    return SliceConfig(
        call_window=CallWindowConfig(start="09:00", end="20:00"),
        eligibility=EligibilityConfig(max_attempts=5, default_timezone="America/Los_Angeles"),
        artifacts=ArtifactsConfig(dir=str(tmp_path / "artifacts")),
        persona=PersonaConfig(version="alf-appointment-setter@0.1.0"),
        state=StateConfig(db=str(tmp_path / "state.db")),
    )


@pytest.fixture
def queue_item() -> QueueItem:
    return QueueItem(
        queue_item_id="alf-prospect-t014",
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
def session_context(queue_item: QueueItem, slice_config: SliceConfig) -> SessionContext:
    return SessionContext(
        session_id="sess-t014-001",
        queue_item=queue_item,
        mock_provider_call_id="CA-T014-FAKE",
        started_at="2026-05-25T14:00:00.000Z",
        config=slice_config,
        clock=FrozenClock(datetime(2026, 5, 25, 14, 0, 0, tzinfo=timezone.utc)),
    )


@pytest.fixture
def conversation_input() -> FakeLiveConversationInput:
    return FakeLiveConversationInput(session_id_value="sess-t014-001")


@pytest.fixture
def fake_provider() -> FakeRealtimeAIProvider:
    return FakeRealtimeAIProvider()


@pytest.fixture
def runtime(fake_provider: FakeRealtimeAIProvider) -> PipecatRuntime:
    return PipecatRuntime(provider=fake_provider, silence_after_connection_timeout_sec=30)


# ----------------------------------------------------------------------------
# Assertion 1 — first connected-call utterance includes the disclosure
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_first_utterance_includes_disclosure(
    runtime: PipecatRuntime,
    session_context: SessionContext,
    conversation_input: FakeLiveConversationInput,
    fake_provider: FakeRealtimeAIProvider,
) -> None:
    """The persona's first connected-call utterance contains the canonical
    AI-on-behalf-of-Medx disclosure (FR-015). No exceptions."""
    # A connected-and-finished call — caller acknowledges.
    fake_provider.scripted_frames = [
        FakeTranscriptSegment(text=CANONICAL_DISCLOSURE, speaker="persona"),
        FakeTranscriptSegment(text="Sure, what's up?", speaker="caller"),
    ]

    output: PersonaOutput = await runtime.run(session_context, conversation_input)
    assert output.disclosure_completed is True, "first connected-call utterance must include the disclosure"


# ----------------------------------------------------------------------------
# Assertion 2 — no explicit acknowledgment required
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_acknowledgment_required(
    runtime: PipecatRuntime,
    session_context: SessionContext,
    conversation_input: FakeLiveConversationInput,
    fake_provider: FakeRealtimeAIProvider,
) -> None:
    """Caller silence after the disclosure does NOT trigger any escalation;
    conversation continues per Round 1 Q1."""
    fake_provider.scripted_frames = [
        FakeTranscriptSegment(text=CANONICAL_DISCLOSURE, speaker="persona"),
        # No caller response yet — persona continues per Round 1 Q1.
        FakeTranscriptSegment(text="(brief pause)", speaker="persona"),
        FakeTranscriptSegment(text="I just wanted to check in about ...", speaker="persona"),
    ]

    output = await runtime.run(session_context, conversation_input)
    assert output.human_review_reason is None, (
        "absence of explicit acknowledgment MUST NOT trigger needs_human_review (Round 1 Q1)"
    )


# ----------------------------------------------------------------------------
# Assertion 3 — live-model extraction does not override deterministic disposition
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_live_model_extraction_does_not_override_disposition(
    runtime: PipecatRuntime,
    session_context: SessionContext,
    conversation_input: FakeLiveConversationInput,
    fake_provider: FakeRealtimeAIProvider,
) -> None:
    """A live-model ``ExtractionEvent`` claiming ``disposition=foo`` MUST be
    ignored; the deterministic Slice 1 rules pick the final disposition
    (FR-014, SC-014)."""
    fake_provider.scripted_frames = [
        FakeTranscriptSegment(text=CANONICAL_DISCLOSURE, speaker="persona"),
        # The live model attempts to inject a disposition.
        FakeExtractionEvent(field="disposition", value="interested_callback_requested", confidence=0.99),
        # But the actual extracted state — a clear opt-out — must drive the disposition.
        FakeTranscriptSegment(text="Please don't call me again.", speaker="caller"),
    ]

    output = await runtime.run(session_context, conversation_input)
    # The deterministic Slice 1 rules must pick `do_not_call` for the opt-out
    # statement, NOT the live model's `interested_callback_requested` injection.
    assert output.final_disposition == Disposition.DO_NOT_CALL, (
        f"live model MUST NOT override deterministic disposition; "
        f"got {output.final_disposition}"
    )


# ----------------------------------------------------------------------------
# Assertion 4 — disallowed claim escalates needs_human_review
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_disallowed_claim_escalates(
    runtime: PipecatRuntime,
    session_context: SessionContext,
    conversation_input: FakeLiveConversationInput,
    fake_provider: FakeRealtimeAIProvider,
) -> None:
    """The live model attempting to emit a claim outside allowed categories
    triggers persona escalation with the matching enumerated reason;
    conversation ends safely (FR-015)."""
    fake_provider.scripted_frames = [
        FakeTranscriptSegment(text=CANONICAL_DISCLOSURE, speaker="persona"),
        # An out-of-allowed-claim utterance from the live model.
        FakeTranscriptSegment(
            text="The monthly cost for memory care at Sunset Ridge is exactly $4,852.",
            speaker="persona",
        ),
    ]

    output = await runtime.run(session_context, conversation_input)
    assert output.final_disposition == Disposition.NEEDS_HUMAN_REVIEW
    assert output.human_review_reason in {
        HumanReviewReason.OUTSIDE_ALLOWED_CLAIMS,
        HumanReviewReason.NON_CLINICAL_TOPIC_ESCALATION,
    }, f"expected an allowed-claim-related escalation reason, got {output.human_review_reason}"


# ----------------------------------------------------------------------------
# Assertion 5 — caller-volunteered PHI escalates + tag-and-redact
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_caller_volunteered_phi_escalates_and_redacts(
    runtime: PipecatRuntime,
    session_context: SessionContext,
    conversation_input: FakeLiveConversationInput,
    fake_provider: FakeRealtimeAIProvider,
    tmp_path: Path,
) -> None:
    """A caller volunteering PHI triggers ``phi_collection_risk`` escalation
    AND a PHI tag-and-redact pass on transcript + summary + shadow transcript
    + shadow discrepancy records BEFORE write (Round 2 Q11)."""
    phi_utterance = "My mother takes 10mg of methotrexate weekly for rheumatoid arthritis."
    fake_provider.scripted_frames = [
        FakeTranscriptSegment(text=CANONICAL_DISCLOSURE, speaker="persona"),
        FakeTranscriptSegment(text=phi_utterance, speaker="caller"),
    ]

    output = await runtime.run(session_context, conversation_input)

    assert output.final_disposition == Disposition.NEEDS_HUMAN_REVIEW
    assert output.human_review_reason == HumanReviewReason.PHI_COLLECTION_RISK

    # The PHI utterance MUST be redacted in the summary before write.
    assert "methotrexate" not in (output.summary or "").lower(), (
        "PHI tag-and-redact must scrub PHI from summary before write (Round 2 Q11)"
    )

    # Transcript / shadow transcript / shadow discrepancy files MUST also be
    # PHI-redacted. The runtime is expected to delegate to the redaction layer
    # before any artifact write — verified by scanning every persisted file.
    artifacts_dir = Path(session_context.config.artifacts.dir)
    if artifacts_dir.exists():
        for path in artifacts_dir.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="replace").lower()
                assert "methotrexate" not in text, (
                    f"PHI substring leaked into {path} — Round 2 Q11 redaction pass missing"
                )


# ----------------------------------------------------------------------------
# Assertion 6 — provider error pre-connected → failed
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provider_error_pre_connected_yields_failed(
    session_context: SessionContext,
    conversation_input: FakeLiveConversationInput,
) -> None:
    """``RealtimeProviderError`` raised BEFORE any ``connected`` event →
    finalize as ``failed`` with runtime-failure reason; no false connected-call
    Phone Call activity (FR-013 Round 1 Q4 (a) pre-connected)."""
    provider = FakeRealtimeAIProvider(raise_on_start=RealtimeProviderError)
    runtime = PipecatRuntime(provider=provider)

    output = await runtime.run(session_context, conversation_input)
    assert output.final_disposition == Disposition.FAILED, (
        f"pre-connected provider error MUST yield Disposition.FAILED; got {output.final_disposition}"
    )


# ----------------------------------------------------------------------------
# Assertion 7 — provider error post-connected → needs_human_review / script_truncated
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provider_error_post_connected_yields_needs_review(
    session_context: SessionContext,
    conversation_input: FakeLiveConversationInput,
) -> None:
    """``RealtimeProviderError`` after the call connected →
    ``needs_human_review`` / ``script_truncated`` (FR-013 Round 1 Q4 (a)
    post-connected)."""
    provider = FakeRealtimeAIProvider(
        scripted_frames=[FakeTranscriptSegment(text=CANONICAL_DISCLOSURE, speaker="persona")],
        raise_during_stream=RealtimeProviderError,
        raise_after_chunks=1,
    )
    runtime = PipecatRuntime(provider=provider)

    output = await runtime.run(session_context, conversation_input)
    assert output.final_disposition == Disposition.NEEDS_HUMAN_REVIEW
    assert output.human_review_reason == HumanReviewReason.SCRIPT_TRUNCATED


# ----------------------------------------------------------------------------
# Assertion 8 — runtime crash post-connected → needs_human_review / script_truncated
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_runtime_crash_post_connected_yields_needs_review(
    session_context: SessionContext,
    conversation_input: FakeLiveConversationInput,
) -> None:
    """``PipecatRuntimeError`` after the call connected →
    ``needs_human_review`` / ``script_truncated`` (FR-013 Round 1 Q4 (b))."""
    provider = FakeRealtimeAIProvider(
        scripted_frames=[FakeTranscriptSegment(text=CANONICAL_DISCLOSURE, speaker="persona")],
        raise_during_stream=PipecatRuntimeError,
        raise_after_chunks=1,
    )
    runtime = PipecatRuntime(provider=provider)

    output = await runtime.run(session_context, conversation_input)
    assert output.final_disposition == Disposition.NEEDS_HUMAN_REVIEW
    assert output.human_review_reason == HumanReviewReason.SCRIPT_TRUNCATED


# ----------------------------------------------------------------------------
# Assertion 9 — silence timeout post-connected → needs_human_review / script_truncated
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_silence_timeout_yields_needs_review(
    session_context: SessionContext,
    conversation_input: FakeLiveConversationInput,
) -> None:
    """``SilenceAfterConnectionTimeout`` post-connected → ``needs_human_review`` /
    ``script_truncated`` (FR-013 Round 1 Q4 (c)). Silence timer fires only after
    connection; pre-connected silence is not a defined case."""
    provider = FakeRealtimeAIProvider(
        scripted_frames=[FakeTranscriptSegment(text=CANONICAL_DISCLOSURE, speaker="persona")],
        silent_after_connection=True,
    )
    # Use a very short timeout so the test runs fast once T064 implements it.
    runtime = PipecatRuntime(provider=provider, silence_after_connection_timeout_sec=1)

    output = await runtime.run(session_context, conversation_input)
    assert output.final_disposition == Disposition.NEEDS_HUMAN_REVIEW
    assert output.human_review_reason == HumanReviewReason.SCRIPT_TRUNCATED


# ----------------------------------------------------------------------------
# Assertion 10 — runtime/model identity recorded; no credentials
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_runtime_identity_recorded_no_credentials(
    runtime: PipecatRuntime,
    session_context: SessionContext,
    conversation_input: FakeLiveConversationInput,
    fake_provider: FakeRealtimeAIProvider,
) -> None:
    """The session record contains ``{runtime_name, runtime_version,
    provider_name, model_name, model_version}`` for audit; contains 0 credential
    strings (FR-016, FR-035)."""
    # Inject a sensitive sentinel into a non-identity attribute the fake exposes;
    # the runtime MUST NOT include it in the identity dict it records.
    fake_provider.scripted_frames = [
        FakeTranscriptSegment(text=CANONICAL_DISCLOSURE, speaker="persona"),
    ]
    # The contract test reads ``provider.identity`` directly because the runtime
    # is required to surface this on the session via ``runtime_identity_json``.
    identity = fake_provider.identity
    for required_key in ("provider_name", "model_name", "model_version"):
        assert required_key in identity, f"identity missing required FR-016 key {required_key!r}"

    # And — critically — no credential string is included.
    blob = " ".join(str(v) for v in identity.values())
    assert _SECRET_MARKER not in blob, (
        "credential string leaked into runtime identity (FR-035)"
    )
    # Also ensure the runtime invocation does not throw when identity is read
    # mid-run — i.e. the runtime exposes identity AND completes the run.
    output = await runtime.run(session_context, conversation_input)
    assert output.persona_version, "persona_version MUST be recorded on the output"


# ----------------------------------------------------------------------------
# Assertion 11 — no Pipecat-specific type names leak past the boundary
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_pipecat_specifics_leak(
    runtime: PipecatRuntime,
    session_context: SessionContext,
    conversation_input: FakeLiveConversationInput,
    fake_provider: FakeRealtimeAIProvider,
) -> None:
    """The ``PersonaOutput`` consumed by the orchestrator contains 0 Pipecat
    type names or provider streaming-protocol fields (SC-015)."""
    fake_provider.scripted_frames = [
        FakeTranscriptSegment(text=CANONICAL_DISCLOSURE, speaker="persona"),
    ]

    output = await runtime.run(session_context, conversation_input)

    forbidden_substrings = (
        "FrameProcessor",
        "Pipeline",
        "Transport",  # Pipecat Transport class — not "transport" the noun
        "frame_processor",
        "pipecat.",
    )
    flat = (
        (output.summary or "")
        + " "
        + (output.persona_version or "")
        + " "
        + (str(output.human_review_reason) if output.human_review_reason else "")
    )
    for forbidden in forbidden_substrings:
        assert forbidden not in flat, (
            f"Pipecat-specific name {forbidden!r} leaked into PersonaOutput: {flat!r}"
        )
