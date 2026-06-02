"""Slice 3 — live-runtime degradation detector + translator (T064).

The three FR-013 degradation triggers (Round 1 Q4) and the contract's
Required-Behavior #5 disposition mapping
(``specs/003-real-call-real-crm/contracts/pipecat-runtime.md``):

- ``RealtimeProviderError`` — provider-side failure (Q4 (a)).
- ``PipecatRuntimeError`` — runtime crash / unrecoverable adapter failure (Q4 (b)).
- ``SilenceAfterConnectionTimeout`` — the deployment-configurable
  silence-after-connection / no-extraction-event timeout elapsed (Q4 (c)).

Each trigger maps to a DISTINCT run-report reason code (Round 4 R4-Q13) so the
run report distinguishes which trigger fired:

- ``RealtimeProviderError`` → ``provider_error``
- ``PipecatRuntimeError`` → ``runtime_crash``
- ``SilenceAfterConnectionTimeout`` → ``silence_timeout``

This module is pure / vendor-neutral — it imports no Pipecat types and only
classifies the three runtime exceptions into ``DegradationOutcome`` records the
runtime (T065) finalizes from. The silence-timeout default is read from
``SLICE3_SILENCE_AFTER_CONNECTION_TIMEOUT_SEC`` (default 30s).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum

from opencloser.models import Disposition, HumanReviewReason
from opencloser.runtime.pipecat.errors import (
    PipecatRuntimeError,
    RealtimeProviderError,
    SilenceAfterConnectionTimeout,
)

# Environment variable + default for the silence-after-connection timeout (Q4 (c)).
SILENCE_TIMEOUT_ENV_VAR = "SLICE3_SILENCE_AFTER_CONNECTION_TIMEOUT_SEC"
DEFAULT_SILENCE_AFTER_CONNECTION_TIMEOUT_SEC = 30


class DegradationReason(StrEnum):
    """Distinct run-report reason codes for the three FR-013 triggers (R4-Q13)."""

    PROVIDER_ERROR = "provider_error"
    RUNTIME_CRASH = "runtime_crash"
    SILENCE_TIMEOUT = "silence_timeout"


# The three FR-013 trigger exception types this module classifies. Any other
# exception is NOT a defined degradation trigger and must propagate.
DEGRADATION_TRIGGERS: tuple[type[Exception], ...] = (
    RealtimeProviderError,
    PipecatRuntimeError,
    SilenceAfterConnectionTimeout,
)


@dataclass(frozen=True, slots=True)
class DegradationOutcome:
    """The finalized disposition + reason for one degradation trigger.

    ``final_disposition`` is ``failed`` for a pre-connected provider/runtime
    failure and ``needs_human_review`` for any post-connected trigger;
    ``human_review_reason`` is ``script_truncated`` only in the post-connected
    case (non-null iff ``final_disposition`` is ``needs_human_review``).
    ``reason_code`` is the distinct run-report code that names which trigger
    fired regardless of pre/post-connected (R4-Q13).
    """

    final_disposition: Disposition
    human_review_reason: HumanReviewReason | None
    reason_code: DegradationReason


def silence_after_connection_timeout_sec(default: int | None = None) -> int:
    """Resolve the configured silence-after-connection timeout in seconds.

    Reads ``SLICE3_SILENCE_AFTER_CONNECTION_TIMEOUT_SEC`` from the environment;
    falls back to ``default`` (the runtime's constructor value) or the module
    default of 30s. A non-integer / non-positive env value is ignored in favor
    of the fallback so a misconfiguration never disables the safety timer.
    """
    raw = os.environ.get(SILENCE_TIMEOUT_ENV_VAR)
    if raw is not None:
        try:
            value = int(raw)
        except ValueError:
            value = 0
        if value > 0:
            return value
    if default is not None and default > 0:
        return default
    return DEFAULT_SILENCE_AFTER_CONNECTION_TIMEOUT_SEC


def is_degradation_trigger(exc: BaseException) -> bool:
    """True iff ``exc`` is one of the three FR-013 degradation triggers."""
    return isinstance(exc, DEGRADATION_TRIGGERS)


def _reason_code_for(exc: BaseException) -> DegradationReason:
    if isinstance(exc, RealtimeProviderError):
        return DegradationReason.PROVIDER_ERROR
    if isinstance(exc, PipecatRuntimeError):
        return DegradationReason.RUNTIME_CRASH
    if isinstance(exc, SilenceAfterConnectionTimeout):
        return DegradationReason.SILENCE_TIMEOUT
    raise TypeError(
        f"{type(exc).__name__} is not an FR-013 degradation trigger; "
        "call is_degradation_trigger() before translating."
    )


def translate(exc: BaseException, *, connected: bool) -> DegradationOutcome:
    """Translate a degradation trigger into the finalized ``DegradationOutcome``.

    Per contract Required-Behavior #5:

    - Pre-connected (``connected is False``) — only ``RealtimeProviderError`` /
      ``PipecatRuntimeError`` can reach here; finalize ``failed`` with the
      matching distinct reason code; no human-review reason.
      ``SilenceAfterConnectionTimeout`` can only fire post-connection by
      construction, so a pre-connected silence trigger is a programming error.
    - Post-connected (``connected is True``) — any of the three triggers
      finalize ``needs_human_review`` / ``script_truncated``; the distinct
      trigger reason code is still recorded.
    """
    reason_code = _reason_code_for(exc)
    if connected:
        return DegradationOutcome(
            final_disposition=Disposition.NEEDS_HUMAN_REVIEW,
            human_review_reason=HumanReviewReason.SCRIPT_TRUNCATED,
            reason_code=reason_code,
        )
    if isinstance(exc, SilenceAfterConnectionTimeout):
        raise ValueError(
            "SilenceAfterConnectionTimeout cannot fire pre-connection — the "
            "silence timer starts on connection (contract Required-Behavior #5)."
        )
    return DegradationOutcome(
        final_disposition=Disposition.FAILED,
        human_review_reason=None,
        reason_code=reason_code,
    )
