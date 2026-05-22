"""Eligibility evaluator — FR-033 module boundary #2.

Contract: see specs/001-mock-call-mock-crm/contracts/eligibility.md
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from opencloser.core.clock import Clock
from opencloser.eligibility.evaluator import BuiltinEligibilityEvaluator
from opencloser.models import EligibilityDecision, QueueItem, SliceConfig

__all__ = ["BuiltinEligibilityEvaluator", "EligibilityEvaluator"]


@runtime_checkable
class EligibilityEvaluator(Protocol):
    """FR-033 contract surface for the eligibility module."""

    def evaluate(
        self,
        queue_item: QueueItem,
        config: SliceConfig,
        clock: Clock,
    ) -> EligibilityDecision:  # pragma: no cover - protocol
        ...
