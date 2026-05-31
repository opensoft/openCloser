"""Slice 3 — `ShadowSTTProvider` + `ShadowSTTLane` contracts (FR-028 — FR-032).

The shadow STT lane is an OPTIONAL non-blocking secondary transcript pipeline
that listens to the same caller audio as the live conversation path. The lane
MUST NOT block the live call, MUST NOT independently write CRM records, and
MUST NOT override the persona's final disposition in the MVP.

The concrete asyncio.Task implementation lands in ``shadow_stt/lane.py`` (US6).
The discrepancy comparison + policy classification lands in
``shadow_stt/discrepancy.py`` (US6). The audit-only ``shadow_lane_truncated``
event writer lands in ``shadow_stt/truncation.py`` (US6).

See ``specs/003-real-call-real-crm/contracts/shadow-stt-lane.md`` for the
full contract.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Literal, Protocol


# 9 atomic enum values mapped from the 7 spec-level high-value field categories
# in FR-030 per data-model.md §1.7 storage normalization. The contract test
# ``test_high_value_fields_enumerated`` (contracts/shadow-stt-lane.md) accepts
# these as the canonical fields the lane compares.
HighValueField = Literal[
    "opt_out",
    "wrong_number",
    "captured_email",
    "callback_intent",
    "preferred_callback_window",
    "person_reached_name",
    "person_reached_role",
    "interest_level",
    "final_disposition",
]


DiscrepancyClassification = Literal["benign", "uncertain"]


class TranscriptSegment(Protocol):
    """One atomic segment of shadow-side transcript output.

    Kept structural so the concrete provider SDK return type does not leak past
    this boundary (Constitution Principle III).
    """

    text: str
    started_at: str  # ISO-8601 UTC ms
    ended_at: str    # ISO-8601 UTC ms


class DiscrepancyEvent(Protocol):
    """One detected divergence between the live conversation path and the shadow
    transcript on a configured high-value field.

    Audit-only: the lane emits these for the orchestrator to consume; the
    orchestrator decides whether to escalate to ``needs_human_review`` /
    ``shadow_stt_discrepancy`` based on ``classification`` AND whether the
    event arrived inside the post-finalization grace window (FR-029 Round 2 Q7).
    """

    session_id: str
    field: HighValueField
    live_value: str  # redacted per FR-033 + Round 2 Q10/Q11
    shadow_value: str  # same redaction policy as live_value
    classification: DiscrepancyClassification
    recorded_at: str  # ISO-8601 UTC ms


class ShadowSTTProvider(Protocol):
    """Deployment-configured shadow STT provider (research.md §4).

    The provider is selected by the ``SLICE3_SHADOW_STT_PROVIDER`` env var. If
    the env var is unset OR equal to ``"disabled"``, the shadow lane is a no-op
    and the FR-032 guarantee ("Slice 3 demonstrable loop completes without it")
    is satisfied.
    """

    async def transcribe(
        self,
        audio_stream: AsyncIterator[bytes],
    ) -> AsyncIterator[TranscriptSegment]:
        """Consume the caller audio stream and yield transcript segments."""
        ...

    async def close(self, session_id: str) -> None:
        """Release provider-side resources for the named session."""
        ...

    @property
    def name(self) -> str:
        """Provider name for audit recording on the session (FR-016)."""
        ...


class ShadowSTTLane(Protocol):
    """The non-blocking secondary transcript lane wrapper.

    The lane runs in its own ``asyncio.Task`` consuming a ``tee``'d copy of the
    caller audio at the ``SignalWireMediaInput`` boundary (research.md §6). The
    orchestrator MUST NOT ``await`` the lane's task before session finalization
    — that would violate FR-029's non-blocking guarantee.
    """

    async def start(
        self,
        session_id: str,
        audio_tee: AsyncIterator[bytes],
    ) -> None:
        """Begin consuming the tee'd audio stream.

        MUST NOT block the caller. MUST NOT raise — provider failures during
        start are recorded as a shadow-lane failure (run report) without
        affecting the live call.
        """
        ...

    async def stop(self, session_id: str) -> None:
        """Signal the lane to finish (orchestrator calls this at finalization).

        MUST NOT block; the lane drains in its own asyncio.Task. Output emitted
        after this call but before the post-finalization grace window elapses
        MAY participate in the disposition (FR-029 Round 2 Q7); output emitted
        after the grace window elapses becomes a ``shadow_lane_truncated`` event
        (audit-only).
        """
        ...

    def detect_discrepancies(
        self,
        live_extraction: dict[HighValueField, str],
    ) -> list[DiscrepancyEvent]:
        """Compare the shadow transcript's extraction against the live extraction
        and return the per-high-value-field discrepancies classified per the
        deployment-configured policy.
        """
        ...

    def truncated_event(self, session_id: str) -> object | None:
        """Return the ``ShadowLaneTruncatedEvent`` record if the lane was still
        producing output AFTER the orchestrator's post-finalization grace window
        elapsed; ``None`` otherwise.

        Audit-only by construction (FR-029): the truncated event MUST NOT mutate
        the finalized disposition, MUST NOT emit a new CRM write-back payload,
        and MUST NOT generate a ``shadow_stt_discrepancy`` review Task.
        """
        ...
