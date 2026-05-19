"""Persona ABC — FR-033 module boundary #4.

Contract: see specs/001-mock-call-mock-crm/contracts/persona.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from opencloser.core.clock import Clock
from opencloser.models import (
    Disposition,
    Extraction,
    HumanReviewReason,
    QueueItem,
    SliceConfig,
)


@dataclass(frozen=True, slots=True)
class SessionContext:
    """Inputs the orchestrator passes to the persona for one connected conversation."""

    session_id: str
    queue_item: QueueItem
    mock_provider_call_id: str
    started_at: str
    config: SliceConfig
    clock: Clock


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    """One turn in a scripted conversation fixture."""

    role: str  # "persona" or "contact"
    text: str


@dataclass(frozen=True, slots=True)
class ConversationFixture:
    """A scripted conversation outcome (research.md §Persona fixture format)."""

    fixture_id: str
    expected_disposition: str  # tests only — persona MUST NOT read this
    queue_item_ref: str
    turns: list[ConversationTurn]
    expected_extraction: dict[str, Any]  # tests only


@dataclass(frozen=True, slots=True)
class PersonaOutput:
    """The persona's structured output for one connected conversation."""

    persona_version: str
    final_disposition: Disposition
    summary: str
    extraction: Extraction
    human_review_reason: HumanReviewReason | None
    disclosure_completed: bool


class Persona(Protocol):
    """FR-009 / FR-011 persona contract surface."""

    @property
    def version(self) -> str:  # pragma: no cover - protocol
        """FR-011 persona version, e.g. `alf-appointment-setter@0.1.0`."""
        ...

    def run(
        self,
        session_context: SessionContext,
        conversation: ConversationFixture,
    ) -> PersonaOutput:  # pragma: no cover - protocol
        """Execute the scripted conversation against the persona's rules."""
        ...
