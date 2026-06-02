"""Slice 3 Pipecat runtime — the concrete ``PersonaRuntime`` implementation
(T030 + US5 T065).

``PipecatRuntime.run`` drives one connected-call conversation:

1. Open a provider session (``RealtimeAIProvider.start_session``). A pre-connection
   ``RealtimeProviderError`` / ``PipecatRuntimeError`` here is a PRE-connected
   degradation: finalize ``failed`` with the runtime-failure reason, no false
   connected-call activity (contract Required-Behavior #5). A *transient*
   ``RealtimeProviderError`` is retried within the connect budget (R4-Q5).
2. Stream the caller audio (from the ``LiveConversationInput``) through the
   provider, collecting the transcript frames it yields. A provider/runtime
   failure raised mid-stream is a POST-connected degradation → finalize
   ``needs_human_review`` / ``script_truncated``. Zero transcript frames after a
   successful connection is the silence-after-connection timeout (Q4 (c)) → same
   post-connected mapping.
3. Record the runtime/model identity (FR-016, via ``identity.py`` T027).
4. Apply the US5 live-conversation safety layer (T065/T066/T067):
   - a disallowed-claim utterance from the live model (persona turn) escalates
     ``needs_human_review`` with ``outside_allowed_claims`` /
     ``non_clinical_topic_escalation`` (contract Required-Behavior #3);
   - a caller-volunteered PHI utterance escalates ``phi_collection_risk`` AND
     runs the redaction layer's PHI tag-and-redact pass over the in-flight
     transcript / summary / shadow buffers BEFORE any artifact write (Round 2 Q11);
   - absence of an explicit acknowledgment after the disclosure is implicit
     acknowledgment — it MUST NOT escalate (Round 1 Q1).
5. Hand the transcript to the persona module, whose **deterministic Slice 1
   disposition precedence** selects the final disposition (FR-014). A live-model
   ``ExtractionEvent`` is never allowed to set the disposition — extraction
   frames are dropped here; only transcript turns reach the persona.

This module MUST NOT leak Pipecat ``FrameProcessor`` / ``Pipeline`` / ``Transport``
types, audio codec / sample-rate / VAD configuration, or the provider's
streaming-protocol details past its public surface (Constitution Principle III;
SC-015) — it imports none of them.
"""

from __future__ import annotations

import contextlib

from opencloser.models import Disposition, HumanReviewReason
from opencloser.persona.alf_appointment_setter import (
    CANONICAL_DISCLOSURE,
    ALFAppointmentSetterPersona,
)
from opencloser.persona.base import (
    ConversationFixture,
    ConversationTurn,
    Persona,
    PersonaOutput,
    SessionContext,
)
from opencloser.redaction.layer import RedactionLayer, apply_phi_redaction_pass
from opencloser.runtime.base import LiveConversationInput, RealtimeAIProvider
from opencloser.runtime.pipecat import degradation
from opencloser.runtime.pipecat.degradation import DegradationOutcome
from opencloser.runtime.pipecat.errors import RealtimeProviderError
from opencloser.runtime.pipecat.identity import build_runtime_identity

# Maximum pre-connection connect attempts when a *transient*
# ``RealtimeProviderError`` is raised on start (R4-Q5). A terminal error (the
# default ``transient=False``) is not retried.
_CONNECT_BUDGET = 3

# Live-model disallowed-claim signals (FR-015). The live model emitting a claim
# outside the allowed categories MUST escalate. These mirror the persona's
# allowed-claim guardrails but are evaluated on PERSONA turns (the live model),
# which the Slice 1 escalation module — scanning CONTACT turns only — does not
# cover.
_DISALLOWED_CLAIM_KEYWORDS = (
    "exactly $",
    "the monthly cost",
    "monthly rate is",
    "the cost is",
    "the price is",
    "costs exactly",
    "is exactly",
)
_NON_CLINICAL_CLAIM_KEYWORDS = (
    "you should take",
    "i recommend you take",
    "the right medication for",
    "the correct dose",
)

# Caller-volunteered PHI signals (Round 2 Q11). Drug names / clinical details a
# caller volunteers despite the persona refusing to ask for them.
_CALLER_PHI_KEYWORDS = (
    "methotrexate",
    "milligram",
    "10mg",
    "mg of",
    "rheumatoid",
    "chemotherapy",
    "diagnosed with",
    "takes ",
    "prescription",
    "medication",
    "dementia",
    "alzheimer",
)


class PipecatRuntime:
    """The ``PersonaRuntime`` Protocol's Slice 3 concrete implementation.

    ``RealtimeAIProvider`` is constructor-injected so contract tests can pass a
    ``FakeRealtimeAIProvider`` without burning real provider credentials. The
    persona defaults to the ALF appointment-setter (the only Slice 1/2/3 persona);
    an explicit ``persona`` may be injected for testing.

    ``shadow_stt_enabled`` (default ``True``) governs the PHI tag-and-redact pass:
    with shadow disabled only the transcript + summary artifacts exist, so the
    pass redacts those two and the absent shadow artifacts are NOT a failure
    (contract Required-Behavior #4 shadow-disabled variant).
    """

    def __init__(
        self,
        *,
        provider: RealtimeAIProvider,
        silence_after_connection_timeout_sec: int = 30,
        persona: Persona | None = None,
        redaction_layer: RedactionLayer | None = None,
        shadow_stt_enabled: bool = True,
    ) -> None:
        self._provider = provider
        self._silence_timeout_sec = degradation.silence_after_connection_timeout_sec(
            silence_after_connection_timeout_sec
        )
        self._persona = persona or ALFAppointmentSetterPersona()
        self._redaction_layer = redaction_layer or RedactionLayer.default()
        self._shadow_stt_enabled = shadow_stt_enabled
        # Surfaced for the run report (T033 / T065): the distinct degradation
        # reason code (provider_error / runtime_crash / silence_timeout) and the
        # recorded runtime/model identity. ``None`` when the call did not degrade.
        self.degradation_reason: str | None = None
        self.phi_volunteered: bool = False

    async def run(
        self,
        session_context: SessionContext,
        conversation: LiveConversationInput,
    ) -> PersonaOutput:
        """Drive the connected-call conversation and return the persona's output.

        See ``contracts/pipecat-runtime.md`` Required Behaviors #1-#6.
        """
        self.degradation_reason = None
        self.phi_volunteered = False

        # ----- connect (pre-connected degradation lives here) ----------------
        try:
            handle = await self._connect(session_context)
        except RealtimeProviderError as exc:  # terminal pre-connection failure
            return self._finalize_degraded(degradation.translate(exc, connected=False))
        except degradation.DEGRADATION_TRIGGERS as exc:  # PipecatRuntimeError on start
            return self._finalize_degraded(degradation.translate(exc, connected=False))

        # ----- stream (post-connected degradation lives here) ----------------
        turns: list[ConversationTurn] = []
        try:
            async for audio_chunk in conversation.audio_in:
                frames = await self._provider.stream_audio(handle, audio_chunk)
                async for frame in frames:
                    turn = _frame_to_turn(frame)
                    if turn is not None:
                        turns.append(turn)
        except degradation.DEGRADATION_TRIGGERS as exc:
            await self._safe_end(handle)
            return self._finalize_degraded(degradation.translate(exc, connected=True))
        await self._safe_end(handle)

        # Record runtime/model identity for audit (FR-016); credentials excluded
        # (FR-035). Held for the run report (T033) to surface.
        self._runtime_identity = build_runtime_identity(self._provider)

        # ----- silence-after-connection timeout (Q4 (c)) ---------------------
        # A connection that produced ZERO transcript frames is the silence /
        # no-extraction-event timeout — finalize post-connected.
        if not turns:
            timeout = degradation.SilenceAfterConnectionTimeout(
                session_id=session_context.session_id,
                timeout_sec=self._silence_timeout_sec,
            )
            return self._finalize_degraded(degradation.translate(timeout, connected=True))

        return self._run_persona_safety(session_context, turns)

    # ------------------------------------------------------------------
    # Connect with transient-retry budget (R4-Q5)
    # ------------------------------------------------------------------

    async def _connect(self, session_context: SessionContext) -> object:
        last_exc: RealtimeProviderError | None = None
        for _ in range(_CONNECT_BUDGET):
            try:
                return await self._provider.start_session(session_context)
            except RealtimeProviderError as exc:
                if not exc.transient:
                    raise
                last_exc = exc
        # Connect budget exhausted on repeated transient errors — finalize as a
        # terminal pre-connection provider failure.
        assert last_exc is not None
        raise last_exc

    async def _safe_end(self, handle: object) -> None:
        # An end_session failure must not mask the conversation outcome.
        with contextlib.suppress(*degradation.DEGRADATION_TRIGGERS):
            await self._provider.end_session(handle)

    # ------------------------------------------------------------------
    # US5 live-conversation safety layer (T065/T066/T067)
    # ------------------------------------------------------------------

    def _run_persona_safety(
        self,
        session_context: SessionContext,
        turns: list[ConversationTurn],
    ) -> PersonaOutput:
        # (3) Allowed-claim guardrails on the LIVE MODEL (persona turns).
        claim_reason = _detect_disallowed_claim(turns)
        if claim_reason is not None:
            return PersonaOutput(
                persona_version=self._persona.version,
                final_disposition=Disposition.NEEDS_HUMAN_REVIEW,
                summary=f"Disposition: needs_human_review; review reason: {claim_reason.value}.",
                extraction=_minimal_extraction(),
                human_review_reason=claim_reason,
                disclosure_completed=_disclosure_completed(turns),
            )

        # (4) Caller-volunteered PHI: escalate phi_collection_risk + redact.
        phi_terms = _detect_caller_phi(turns)
        if phi_terms:
            self.phi_volunteered = True
            return self._finalize_phi(session_context, turns, phi_terms)

        # The persona module owns the deterministic disposition precedence
        # (FR-014). Live-model extraction frames never reach it.
        output = self._persona.run(session_context, _as_fixture(session_context, turns))

        # (2/Round 1 Q1) No explicit acknowledgment required: a connected call
        # where the persona spoke (frames present) but the caller never produced
        # a disposition-driving turn must NOT escalate needs_human_review. The
        # deterministic persona maps that to `script_truncated`; here we treat
        # absence of acknowledgment as implicit acknowledgment and clear the
        # escalation rather than surfacing a false human-review.
        if (
            output.human_review_reason is HumanReviewReason.SCRIPT_TRUNCATED
            and output.disclosure_completed
            and _no_contact_signal(turns)
        ):
            return PersonaOutput(
                persona_version=output.persona_version,
                final_disposition=Disposition.NO_ANSWER,
                summary="Disposition: no_answer; caller did not respond after disclosure.",
                extraction=output.extraction,
                human_review_reason=None,
                disclosure_completed=True,
            )
        return output

    def _finalize_phi(
        self,
        session_context: SessionContext,
        turns: list[ConversationTurn],
        phi_terms: list[str],
    ) -> PersonaOutput:
        """Escalate ``phi_collection_risk`` and run the redaction pass on every
        in-flight artifact buffer BEFORE any write (Round 2 Q11)."""
        transcript_text = "\n".join(f"[{t.role}] {t.text}" for t in turns)
        raw_summary = (
            f"Disposition: needs_human_review; review reason: "
            f"{HumanReviewReason.PHI_COLLECTION_RISK.value}. {transcript_text}"
        )
        # With shadow STT disabled only transcript + summary exist; redact those
        # two and treat the absent shadow artifacts as not-present (not a failure).
        shadow_transcript = transcript_text if self._shadow_stt_enabled else None
        shadow_discrepancies = [transcript_text] if self._shadow_stt_enabled else []
        redacted = apply_phi_redaction_pass(
            self._redaction_layer,
            transcript_text=transcript_text,
            summary_text=raw_summary,
            shadow_transcript_text=shadow_transcript,
            shadow_discrepancy_texts=shadow_discrepancies,
            phi_terms=phi_terms,
        )
        # Hold the redacted buffers for the orchestrator/artifact writer (T067).
        self.redacted_artifacts = redacted
        redacted_summary = redacted.get("summary")
        summary = redacted_summary if isinstance(redacted_summary, str) else raw_summary
        del session_context  # PHI escalation is conversation-driven; context unused here
        return PersonaOutput(
            persona_version=self._persona.version,
            final_disposition=Disposition.NEEDS_HUMAN_REVIEW,
            summary=summary[:200],
            extraction=_minimal_extraction(),
            human_review_reason=HumanReviewReason.PHI_COLLECTION_RISK,
            disclosure_completed=_disclosure_completed(turns),
        )

    def _finalize_degraded(self, outcome: DegradationOutcome) -> PersonaOutput:
        """Build the ``PersonaOutput`` for a degradation trigger and stamp the
        distinct run-report reason code (R4-Q13)."""
        self.degradation_reason = outcome.reason_code.value
        if outcome.final_disposition is Disposition.FAILED:
            summary = (
                f"Disposition: failed; runtime degradation ({outcome.reason_code.value})."
            )
        else:
            summary = (
                f"Disposition: needs_human_review; review reason: "
                f"{HumanReviewReason.SCRIPT_TRUNCATED.value} ({outcome.reason_code.value})."
            )
        return PersonaOutput(
            persona_version=self._persona.version,
            final_disposition=outcome.final_disposition,
            summary=summary,
            extraction=_minimal_extraction(),
            human_review_reason=outcome.human_review_reason,
            disclosure_completed=False,
        )


def _as_fixture(
    session_context: SessionContext, turns: list[ConversationTurn]
) -> ConversationFixture:
    return ConversationFixture(
        fixture_id=session_context.session_id,
        expected_disposition="",  # tests-only field; the persona ignores it
        queue_item_ref=session_context.queue_item.queue_item_id,
        turns=turns,
        expected_extraction={},
    )


def _frame_to_turn(frame: object) -> ConversationTurn | None:
    """Map a provider transcript frame to a conversation turn.

    Duck-typed so both the in-tree ``provider.py`` frames and the contract-test
    fakes work. Non-transcript frames (extraction / audio) return ``None`` — an
    ``ExtractionEvent`` MUST NOT influence the disposition (FR-014), so it never
    becomes a turn. Extraction frames are distinguished by carrying a ``field``
    attribute (and no ``speaker``).
    """
    if getattr(frame, "field", None) is not None and getattr(frame, "speaker", None) is None:
        return None
    text = getattr(frame, "text", None)
    speaker = getattr(frame, "speaker", None)
    if text is None or speaker is None:
        return None
    role = "persona" if speaker == "persona" else "contact"
    return ConversationTurn(role=role, text=text)


def _disclosure_completed(turns: list[ConversationTurn]) -> bool:
    persona_turns = [t for t in turns if t.role == "persona"]
    return bool(persona_turns) and persona_turns[0].text == CANONICAL_DISCLOSURE


def _no_contact_signal(turns: list[ConversationTurn]) -> bool:
    """True iff the caller never produced a substantive turn (silent after the
    disclosure). A connected call with only persona turns is the no-ack case."""
    return not any(t.role == "contact" for t in turns)


def _detect_disallowed_claim(turns: list[ConversationTurn]) -> HumanReviewReason | None:
    """Detect a live-model (persona turn) claim outside the allowed categories."""
    persona_text = " ".join(t.text.lower() for t in turns if t.role == "persona")
    if any(k in persona_text for k in _NON_CLINICAL_CLAIM_KEYWORDS):
        return HumanReviewReason.NON_CLINICAL_TOPIC_ESCALATION
    if any(k in persona_text for k in _DISALLOWED_CLAIM_KEYWORDS):
        return HumanReviewReason.OUTSIDE_ALLOWED_CLAIMS
    return None


def _detect_caller_phi(turns: list[ConversationTurn]) -> list[str]:
    """Return the PHI-signal terms the caller volunteered (empty if none).

    Matching is done on the lowercased caller text; the returned terms are the
    matched keywords, which the redaction pass scrubs (case-insensitively) from
    every in-flight artifact buffer before write (Round 2 Q11).
    """
    caller_text = " ".join(t.text.lower() for t in turns if t.role == "contact")
    return [k.strip() for k in _CALLER_PHI_KEYWORDS if k in caller_text]


def _minimal_extraction():
    from opencloser.models import Extraction, IntentClassification, RoleConfidence

    return Extraction(
        captured_email=None,
        captured_email_unverified=None,
        callback_requested=False,
        preferred_callback_window=None,
        role_confidence=RoleConfidence.UNCERTAIN,
        intent_classification=IntentClassification.UNCERTAIN,
        refusal_topics=[],
    )
