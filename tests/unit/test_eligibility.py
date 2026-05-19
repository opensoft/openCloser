"""Unit tests for BuiltinEligibilityEvaluator (FR-004 + Clarifications Round 2)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from opencloser.core.clock import FrozenClock
from opencloser.eligibility.evaluator import BuiltinEligibilityEvaluator
from opencloser.models import (
    ArtifactsConfig,
    CallWindowConfig,
    CallableStatus,
    EligibilityConfig,
    PersonaConfig,
    QueueItem,
    SliceConfig,
    StateConfig,
)

pytestmark = pytest.mark.module("eligibility")


def _config(
    *,
    start: str = "09:00",
    end: str = "20:00",
    max_attempts: int = 5,
    default_tz: str = "America/Los_Angeles",
) -> SliceConfig:
    return SliceConfig(
        call_window=CallWindowConfig(start=start, end=end),
        eligibility=EligibilityConfig(max_attempts=max_attempts, default_timezone=default_tz),
        artifacts=ArtifactsConfig(dir="./artifacts"),
        persona=PersonaConfig(version="alf-appointment-setter@0.1.0"),
        state=StateConfig(db="./state/slice1.db"),
    )


def _eligible_item(**overrides: object) -> QueueItem:
    base: dict[str, object] = {
        "queue_item_id": "q1",
        "facility_name": "Sunset Ridge",
        "phone_number": "+15555550100",
        "timezone": "America/Los_Angeles",
        "attempt_count": 0,
        "callable_status": CallableStatus.READY,
    }
    base.update(overrides)
    return QueueItem(**base)  # type: ignore[arg-type]


def _clock_at_noon_pacific() -> FrozenClock:
    """2026-05-19 19:00:00 UTC = 12:00:00 Pacific (during DST, UTC-7)."""
    return FrozenClock(datetime(2026, 5, 19, 19, 0, 0, tzinfo=UTC))


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_all_rules_pass_yields_allow() -> None:
    evaluator = BuiltinEligibilityEvaluator()
    decision = evaluator.evaluate(_eligible_item(), _config(), _clock_at_noon_pacific())
    assert decision.outcome == "allow"
    assert decision.failing_rules == []
    assert decision.rule_a_phone_pass and decision.rule_b_timezone_pass
    assert decision.rule_c_call_window_pass and decision.rule_d_dnc_pass
    assert decision.rule_e_max_attempts_pass and decision.rule_f_callable_status_pass


# ---------------------------------------------------------------------------
# Per-rule failure (no short-circuit)
# ---------------------------------------------------------------------------


def test_rule_a_phone_presence_null() -> None:
    evaluator = BuiltinEligibilityEvaluator()
    decision = evaluator.evaluate(_eligible_item(phone_number=None), _config(), _clock_at_noon_pacific())
    assert decision.outcome == "block"
    assert decision.failing_rules == ["a"]
    assert decision.rule_a_phone_pass is False


def test_rule_a_phone_presence_whitespace_only() -> None:
    """Q13: non-null AND non-empty after trim."""
    evaluator = BuiltinEligibilityEvaluator()
    decision = evaluator.evaluate(_eligible_item(phone_number="   "), _config(), _clock_at_noon_pacific())
    assert decision.outcome == "block"
    assert decision.failing_rules == ["a"]


def test_rule_b_default_tz_fallback_passes_with_substituted_for() -> None:
    """Edge Case: missing/malformed timezone → default applied, recorded in decision."""
    evaluator = BuiltinEligibilityEvaluator()
    decision = evaluator.evaluate(
        _eligible_item(timezone="Not/A_Real_Zone"), _config(), _clock_at_noon_pacific()
    )
    assert decision.rule_b_timezone_pass is True
    assert decision.default_tz_substituted_for == "Not/A_Real_Zone"


def test_rule_c_outside_call_window_blocks() -> None:
    evaluator = BuiltinEligibilityEvaluator()
    # 2026-05-19 04:00 UTC = 21:00 the previous day Pacific (during DST, UTC-7).
    # Wait — UTC-7 means 04:00 UTC = 21:00 the prior day local. To get a clear "outside window"
    # case during May 19 we want 03:00 UTC on May 20 → 20:00 May 19 Pacific. Actually 20:00
    # is the inclusive end so it should PASS. Let's use 03:01 UTC May 20 → 20:01 May 19 Pacific = outside.
    early_morning_utc = FrozenClock(datetime(2026, 5, 20, 3, 1, 0, tzinfo=UTC))
    decision = evaluator.evaluate(_eligible_item(), _config(), early_morning_utc)
    assert decision.outcome == "block"
    assert "c" in decision.failing_rules


def test_rule_c_inclusive_end_boundary_at_2000() -> None:
    """Q12: 20:00 local is allowed (inclusive end)."""
    evaluator = BuiltinEligibilityEvaluator()
    # 2026-05-20 03:00:00 UTC = 20:00:00 May 19 Pacific (UTC-7 during DST).
    at_eight_pm = FrozenClock(datetime(2026, 5, 20, 3, 0, 0, tzinfo=UTC))
    decision = evaluator.evaluate(_eligible_item(), _config(), at_eight_pm)
    assert decision.rule_c_call_window_pass is True


def test_rule_d_dnc_flag_blocks() -> None:
    evaluator = BuiltinEligibilityEvaluator()
    decision = evaluator.evaluate(_eligible_item(dnc_flag=True), _config(), _clock_at_noon_pacific())
    assert decision.outcome == "block"
    assert "d" in decision.failing_rules
    assert decision.rule_d_dnc_pass is False


def test_rule_e_attempts_at_max_blocks() -> None:
    evaluator = BuiltinEligibilityEvaluator()
    decision = evaluator.evaluate(_eligible_item(attempt_count=5), _config(), _clock_at_noon_pacific())
    assert decision.outcome == "block"
    assert "e" in decision.failing_rules


def test_rule_f_callable_status_blocks_when_not_ready() -> None:
    evaluator = BuiltinEligibilityEvaluator()
    for not_ready in (
        CallableStatus.IN_PROGRESS,
        CallableStatus.COMPLETED,
        CallableStatus.BLOCKED,
        CallableStatus.DNC,
    ):
        decision = evaluator.evaluate(
            _eligible_item(callable_status=not_ready), _config(), _clock_at_noon_pacific()
        )
        assert decision.outcome == "block", not_ready
        assert "f" in decision.failing_rules


# ---------------------------------------------------------------------------
# Multi-rule failure: no short-circuit
# ---------------------------------------------------------------------------


def test_multi_rule_failure_lists_all_in_canonical_order() -> None:
    """FR-004: when multiple rules fail, the decision lists every one in (a)–(f) order."""
    evaluator = BuiltinEligibilityEvaluator()
    decision = evaluator.evaluate(
        _eligible_item(
            phone_number=None,           # fails (a)
            dnc_flag=True,                # fails (d)
            callable_status=CallableStatus.DNC,  # fails (f)
        ),
        _config(),
        _clock_at_noon_pacific(),
    )
    assert decision.outcome == "block"
    assert decision.failing_rules == ["a", "d", "f"]


# ---------------------------------------------------------------------------
# Default-tz fallback when timezone is None
# ---------------------------------------------------------------------------


def test_rule_b_null_timezone_falls_back_silently() -> None:
    """When queue record has no timezone at all, default is used and substitution is None (no original)."""
    evaluator = BuiltinEligibilityEvaluator()
    decision = evaluator.evaluate(_eligible_item(timezone=None), _config(), _clock_at_noon_pacific())
    assert decision.rule_b_timezone_pass is True
    assert decision.default_tz_substituted_for is None
