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
    # A valid record-supplied timezone means no default substitution (H3).
    assert decision.default_tz_applied is False
    assert decision.default_tz_substituted_for is None


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
    assert decision.default_tz_applied is True
    assert decision.default_tz_substituted_for == "Not/A_Real_Zone"


def test_rule_c_just_past_end_boundary_blocks() -> None:
    """Q12: 20:01 local — one minute past the inclusive 20:00 end — is blocked."""
    evaluator = BuiltinEligibilityEvaluator()
    # 2026-05-20 03:01:00 UTC = 20:01:00 May 19 Pacific (UTC-7 during DST).
    at_8_01_pm = FrozenClock(datetime(2026, 5, 20, 3, 1, 0, tzinfo=UTC))
    decision = evaluator.evaluate(_eligible_item(), _config(), at_8_01_pm)
    assert decision.outcome == "block"
    assert "c" in decision.failing_rules


def test_rule_c_inclusive_end_boundary_at_2000() -> None:
    """Q12: 20:00 local is allowed (inclusive end)."""
    evaluator = BuiltinEligibilityEvaluator()
    # 2026-05-20 03:00:00 UTC = 20:00:00 May 19 Pacific (UTC-7 during DST).
    at_eight_pm = FrozenClock(datetime(2026, 5, 20, 3, 0, 0, tzinfo=UTC))
    decision = evaluator.evaluate(_eligible_item(), _config(), at_eight_pm)
    assert decision.rule_c_call_window_pass is True


def test_rule_c_inclusive_start_boundary_at_0900() -> None:
    """Q12: 09:00 local is allowed (inclusive start)."""
    evaluator = BuiltinEligibilityEvaluator()
    # 2026-05-19 16:00:00 UTC = 09:00:00 May 19 Pacific (UTC-7 during DST).
    at_nine_am = FrozenClock(datetime(2026, 5, 19, 16, 0, 0, tzinfo=UTC))
    decision = evaluator.evaluate(_eligible_item(), _config(), at_nine_am)
    assert decision.rule_c_call_window_pass is True


def test_rule_c_dst_spring_forward_applies_post_transition_offset() -> None:
    """Q14: zoneinfo handles DST. US Pacific springs forward 2026-03-08 02:00 →
    03:00, so that evening Pacific is PDT (UTC-7). A UTC instant therefore resolves
    one hour later than it would under PST — asserting the boundary proves DST applied."""
    evaluator = BuiltinEligibilityEvaluator()
    # 2026-03-09 03:00 UTC = 20:00 Mar 8 PDT (inclusive end) — allowed.
    at_8pm_pdt = FrozenClock(datetime(2026, 3, 9, 3, 0, 0, tzinfo=UTC))
    assert evaluator.evaluate(_eligible_item(), _config(), at_8pm_pdt).rule_c_call_window_pass is True
    # 2026-03-09 04:00 UTC = 21:00 Mar 8 PDT — blocked. Under PST this same instant
    # would be 20:00 and wrongly pass, so asserting block confirms the DST offset.
    at_9pm_pdt = FrozenClock(datetime(2026, 3, 9, 4, 0, 0, tzinfo=UTC))
    decision = evaluator.evaluate(_eligible_item(), _config(), at_9pm_pdt)
    assert decision.rule_c_call_window_pass is False
    assert "c" in decision.failing_rules


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
    # The default WAS applied even though there is no original value to record (H3).
    assert decision.default_tz_applied is True
    assert decision.default_tz_substituted_for is None


# ---------------------------------------------------------------------------
# Invalid configured default timezone
# ---------------------------------------------------------------------------


def test_invalid_default_timezone_fails_rule_b() -> None:
    """A bogus configured default_timezone fails rule (b) outright instead of
    silently passing (b) and surfacing only as a rule (c) failure."""
    evaluator = BuiltinEligibilityEvaluator()
    bad_tz_config = _config(default_tz="Not/A_Real_Zone")
    decision = evaluator.evaluate(
        _eligible_item(timezone=None), bad_tz_config, _clock_at_noon_pacific()
    )
    assert decision.rule_b_timezone_pass is False
    assert decision.rule_c_call_window_pass is False  # window cannot be computed
    assert decision.outcome == "block"
    assert decision.failing_rules == ["b", "c"]
    assert decision.default_tz_applied is True


def test_invalid_default_timezone_ignored_when_record_tz_valid() -> None:
    """When the record carries a usable timezone the configured default is never
    consulted, so a bogus default does not affect rule (b)."""
    evaluator = BuiltinEligibilityEvaluator()
    bad_tz_config = _config(default_tz="Not/A_Real_Zone")
    decision = evaluator.evaluate(
        _eligible_item(timezone="America/Los_Angeles"), bad_tz_config, _clock_at_noon_pacific()
    )
    assert decision.rule_b_timezone_pass is True
    assert decision.outcome == "allow"


# ---------------------------------------------------------------------------
# EligibilityDecision envelope shape
# ---------------------------------------------------------------------------


def test_decision_envelope_shape() -> None:
    """The decision carries a prefixed decision_id, a UTC-ms decided_at, and an
    unset session_id (the orchestrator backfills session_id after session creation)."""
    evaluator = BuiltinEligibilityEvaluator()
    decision = evaluator.evaluate(_eligible_item(), _config(), _clock_at_noon_pacific())
    assert decision.decision_id.startswith("dec_")
    assert decision.queue_item_id == "q1"
    assert decision.decided_at == "2026-05-19T19:00:00.000Z"
    assert decision.session_id == ""
