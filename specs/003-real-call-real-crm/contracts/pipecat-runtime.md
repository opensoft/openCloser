# Contract: Pipecat Realtime Audio Runtime + Real-time AI Provider

**Slice 3** · **FR-013 – FR-016** (+ Round 1 Q4 degradation triggers, Round 2 Q11 PHI escalation) · [plan.md](../plan.md) · [research.md §3, §5, §7](../research.md)

The Pipecat runtime adapter is the Slice 3 implementation of the Slice 1 persona conceptual
contract. It MUST satisfy the existing `run(session_context, conversation) → PersonaOutput`
signature, bridge connected-call audio between the SignalWire transport and a
deployment-configured real-time AI model provider, and deliver transcript / extraction
events to the persona module so the deterministic Slice 1 disposition precedence selects
the final disposition. The live model MUST NOT set the disposition.

## Python protocol (consumed by the orchestrator)

```python
from typing import Protocol, AsyncIterator
from opencloser.persona.base import SessionContext, PersonaOutput
from opencloser.runtime.base import LiveConversationInput
from opencloser.models import AudioChunk, TranscriptSegment, ExtractionEvent  # frame types

class PersonaRuntime(Protocol):
    """Slice 1 conceptual contract; Pipecat implementation for Slice 3."""

    async def run(
        self,
        session_context: SessionContext,
        conversation: LiveConversationInput,
    ) -> PersonaOutput:
        """Drive the connected-call conversation. Returns the persona's
        output for the orchestrator to assemble into the normalized session
        result.

        The runtime MUST:
        - deliver the persona's first connected-call utterance with the
          canonical AI-on-behalf-of-Medx disclosure (FR-015).
        - NOT require explicit verbal acknowledgment after the disclosure;
          absence of an opt-out → implicit acknowledgment (Round 1 Q1).
        - emit extraction events the persona module consumes to populate
          the Slice 1 extraction schema (FR-014).
        - escalate `needs_human_review` with the appropriate Slice 1
          enumerated reason on out-of-allowed-claim / non-clinical-topic /
          PHI attempts by the live model.
        - escalate `needs_human_review` with reason `phi_collection_risk`
          AND tag-and-redact the PHI-bearing utterance in transcript +
          summary + shadow transcript + shadow discrepancy records before
          write when a caller VOLUNTEERS PHI (Round 2 Q11).
        - NOT set the final disposition; the persona module's deterministic
          rules (FR-014) own that decision.

        Raises:
            RealtimeProviderError: provider-side failure (Round 1 Q4 (a)).
            PipecatRuntimeError: runtime crash / unrecoverable adapter
                failure (Round 1 Q4 (b)).
            SilenceAfterConnectionTimeout: configurable silence /
                no-extraction-event timeout elapsed (Round 1 Q4 (c)).
        """


class RealtimeAIProvider(Protocol):
    """Deployment-configured real-time AI provider; consumed by Pipecat."""

    async def start_session(self, session_context: SessionContext) -> "SessionHandle": ...

    async def stream_audio(
        self,
        handle: "SessionHandle",
        audio_chunk: AudioChunk,
    ) -> AsyncIterator[AudioChunk | TranscriptSegment | ExtractionEvent]: ...

    async def end_session(self, handle: "SessionHandle") -> None: ...

    @property
    def identity(self) -> dict[str, str]:
        """Returns {provider_name, model_name, model_version} for audit
        (FR-016). MUST NOT include credentials (FR-035)."""
```

## Required behaviors

1. **AI disclosure on every connected call** (FR-015): the persona's first connected-call
   utterance MUST include the canonical AI-on-behalf-of-Medx disclosure. No exceptions.
   No explicit verbal acknowledgment required (Round 1 Q1).

2. **Deterministic disposition precedence preserved** (FR-014): the live model MAY produce
   conversation turns and `ExtractionEvent`s, but the persona module's deterministic
   disposition rules (Slice 1 FR-036) MUST select the final disposition. The live model
   MUST NOT change which disposition is selected for a given extracted state. The persona's
   `human_review_reason` enumeration MUST NOT be expanded or replaced by the live model
   (only the additive `shadow_stt_discrepancy` entry — emitted from the shadow lane, not
   the live model — is sanctioned).

3. **Allowed-claim guardrails preserved** (FR-015): the live model attempting to emit a
   claim outside the allowed-claim categories MUST trigger persona escalation with the
   appropriate enumerated reason (`outside_allowed_claims`, `non_clinical_topic_escalation`,
   `phi_collection_risk`). The conversation MUST end safely.

4. **Caller-volunteered PHI** (FR-015 / FR-033 per Round 2 Q11): when a caller volunteers
   PHI despite the persona refusing to ask for it, the persona MUST:
   - Escalate `needs_human_review` with reason `phi_collection_risk`.
   - Trigger the redaction layer's PHI tag-and-redact pass before any of
     {transcript, session-result summary, shadow STT transcript, shadow STT discrepancy
     records} is written to disk.
   - The call MAY continue or end per the persona's existing decision rules.
   - The PHI-volunteered case MUST be observably distinct from a non-PHI call in the audit
     artifacts and the run report.

5. **Live-runtime degradation triggers** (FR-013 per Round 1 Q4): any of the three triggers
   below MUST result in orchestrator finalization with the disposition mapping below:
   - (a) `RealtimeProviderError` from the configured real-time AI provider.
   - (b) `PipecatRuntimeError` (runtime crash / unrecoverable adapter failure).
   - (c) `SilenceAfterConnectionTimeout` — the deployment-configurable silence-after-connection
     / no-extraction-event timeout elapsed.

   Disposition mapping:
   - Pre-connected (triggers (a) and (b) only): finalize as `failed` with a runtime-failure
     reason; no false connected-call Phone Call activity.
   - Post-connected (any of (a) / (b) / (c)): finalize as `needs_human_review` with reason
     `script_truncated`.

6. **Runtime/model identity recorded** (FR-016): every session MUST record
   `{runtime_name, runtime_version, provider_name, model_name, model_version}`. Credentials
   MUST NOT be recorded (FR-035).

## What MUST NOT leak past this boundary

- Pipecat-specific `FrameProcessor` / `Pipeline` / `Transport` types.
- The real-time AI provider's streaming protocol details (wire format, framing).
- Audio codec / sample rate / VAD configuration.
- The provider's SDK return types beyond the protocol shape above.
- Credentials.

## Contract test summary (`tests/contract/test_pipecat_runtime.py`)

| Test | Assertion |
|---|---|
| `test_first_utterance_includes_disclosure` | The persona's first connected-call utterance contains the canonical AI-on-behalf-of-Medx disclosure |
| `test_no_acknowledgment_required` | Caller silence after disclosure does NOT trigger any escalation; conversation continues |
| `test_live_model_extraction_does_not_override_disposition` | A live-model `ExtractionEvent` claiming `disposition=foo` is ignored; deterministic Slice 1 rules pick the final disposition |
| `test_disallowed_claim_escalates` | Live model emits a claim outside allowed categories → persona escalates `needs_human_review` with the matching reason; conversation ends safely |
| `test_caller_volunteered_phi_escalates_and_redacts` | Caller volunteers PHI → `phi_collection_risk` escalation + PHI tag-and-redact pass runs on all four artifact types before write |
| `test_provider_error_pre_connected_yields_failed` | `RealtimeProviderError` raised before any `connected` event → finalize as `failed` with runtime-failure reason; no Phone Call activity |
| `test_provider_error_post_connected_yields_needs_review` | `RealtimeProviderError` raised after `connected` → finalize as `needs_human_review` / `script_truncated` |
| `test_runtime_crash_post_connected_yields_needs_review` | `PipecatRuntimeError` after `connected` → finalize as `needs_human_review` / `script_truncated` |
| `test_silence_timeout_yields_needs_review` | `SilenceAfterConnectionTimeout` after `connected` → finalize as `needs_human_review` / `script_truncated` |
| `test_runtime_identity_recorded_no_credentials` | Session record contains `{runtime_name, version, provider_name, model_name, model_version}`; contains 0 credential strings |
| `test_no_pipecat_specifics_leak` | The `PersonaOutput` consumed by the orchestrator contains 0 Pipecat type names or provider streaming protocol fields (SC-015) |
