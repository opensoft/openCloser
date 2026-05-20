"""BuiltinEligibilityEvaluator — applies the six FR-004 rules in canonical order.

Contract: see specs/001-mock-call-mock-crm/contracts/eligibility.md
"""

from __future__ import annotations

from datetime import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from opencloser.core import ids
from opencloser.core.clock import Clock
from opencloser.models import (
    CallableStatus,
    EligibilityDecision,
    QueueItem,
    RuleCode,
    SliceConfig,
)

_RULE_ORDER: tuple[RuleCode, ...] = ("a", "b", "c", "d", "e", "f")


class BuiltinEligibilityEvaluator:
    """Slice 1 eligibility evaluator (pure; orchestrator persists the decision)."""

    def evaluate(
        self,
        queue_item: QueueItem,
        config: SliceConfig,
        clock: Clock,
    ) -> EligibilityDecision:
        # Rule (a) — phone presence: Q13 says non-null AND non-empty after trim.
        rule_a = bool(queue_item.phone_number and queue_item.phone_number.strip())

        # Rule (b) — usable timezone: the record's own zone or, when that is
        # missing/unparseable, the configured default. The resolved zone MUST
        # itself be parseable; a bogus configured default fails rule (b) here
        # rather than silently passing (b) and surfacing only as a rule (c) failure.
        tz_name, default_tz_applied, default_tz_substituted_for, rule_b = _resolve_timezone(
            queue_item, config
        )

        # Rule (c) — current local time within the configured call window.
        rule_c = _is_within_call_window(
            tz_name=tz_name,
            start_str=config.call_window.start,
            end_str=config.call_window.end,
            clock=clock,
        )

        # Rule (d) — DNC / opt-out flag NOT set.
        rule_d = not queue_item.dnc_flag

        # Rule (e) — attempt count below configured maximum.
        rule_e = queue_item.attempt_count < config.eligibility.max_attempts

        # Rule (f) — callable_status equals `ready`.
        rule_f = queue_item.callable_status is CallableStatus.READY

        pass_map: dict[RuleCode, bool] = {
            "a": rule_a,
            "b": rule_b,
            "c": rule_c,
            "d": rule_d,
            "e": rule_e,
            "f": rule_f,
        }
        failing_rules: list[RuleCode] = [r for r in _RULE_ORDER if not pass_map[r]]
        outcome = "allow" if not failing_rules else "block"

        return EligibilityDecision(
            decision_id=ids.new_decision_id(),
            queue_item_id=queue_item.queue_item_id,
            decided_at=clock.now_utc_ms(),
            outcome=outcome,  # type: ignore[arg-type]
            rule_a_phone_pass=rule_a,
            rule_b_timezone_pass=rule_b,
            rule_c_call_window_pass=rule_c,
            rule_d_dnc_pass=rule_d,
            rule_e_max_attempts_pass=rule_e,
            rule_f_callable_status_pass=rule_f,
            failing_rules=failing_rules,
            default_tz_applied=default_tz_applied,
            default_tz_substituted_for=default_tz_substituted_for,
            session_id="",  # backfilled by the orchestrator after session creation
        )


def _resolve_timezone(
    queue_item: QueueItem, config: SliceConfig
) -> tuple[str, bool, str | None, bool]:
    """Return (tz_name, default_tz_applied, default_tz_substituted_for, rule_b_pass).

    If the record's timezone is None or unparseable, fall back to the configured default,
    flag `default_tz_applied=True`, and record the original value (None or the unparseable
    string) in `default_tz_substituted_for` so the substitution is visible in the persisted
    decision (spec Edge Case "Missing or malformed timezone on the record").

    `rule_b_pass` is True only when the resolved zone — the record's own or the substituted
    default — is itself parseable by `zoneinfo`. A bogus configured default therefore fails
    rule (b) instead of silently passing it.
    """
    original = queue_item.timezone
    if original is not None and _is_parseable_tz(original):
        return original, False, None, True
    # Record timezone is missing or unparseable — substitute the configured default.
    default_tz = config.eligibility.default_timezone
    return default_tz, True, original, _is_parseable_tz(default_tz)


def _is_parseable_tz(tz_name: str) -> bool:
    """True when `tz_name` resolves via `zoneinfo.ZoneInfo` (which also handles DST)."""
    try:
        ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True


def _is_within_call_window(*, tz_name: str, start_str: str, end_str: str, clock: Clock) -> bool:
    """Q12 — `[start, end]` both ends inclusive at minute resolution; applies all 7 days (Q11)."""
    try:
        local = clock.now_local(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    start = _parse_hhmm(start_str)
    end = _parse_hhmm(end_str)
    now_local_time = time(local.hour, local.minute)
    return start <= now_local_time <= end


def _parse_hhmm(value: str) -> time:
    hours, minutes = value.split(":", 1)
    return time(int(hours), int(minutes))
