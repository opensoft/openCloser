"""T045 — Slice 3 telephony readiness checker (FR-009 - FR-011).

Before any real-call / write-enabled SignalWire dial, the run MUST pass a hard
telephony readiness check covering the nine FR-009 categories (data-model §1.9).
This module owns the check logic and produces a
:class:`~opencloser.models.TelephonyReadinessReport` with one per-check
``pass`` / ``fail`` entry + a human-readable detail. The runner (T046) gates the
dial on :pyattr:`TelephonyReadinessReport.all_pass` and, on failure, exits with
code 4 having placed zero SignalWire calls and consumed zero attempts.

The Round 4 additions to the FR-009 set (real-time-AI / shadow-STT credentials,
the signing-secret check, the ``{session_id}``-only placeholder validation, and
the Dynamics ``shadow_stt_discrepancy`` option-set check) land in T110; this
module implements the nine base FR-009 checks that the ``TelephonyReadinessCheckName``
enum pins.
"""

from __future__ import annotations

from dataclasses import dataclass

from opencloser.models import (
    QueueItem,
    TelephonyReadinessCheckName,
    TelephonyReadinessCheckResult,
    TelephonyReadinessReport,
    TelephonyReadinessResult,
)
from opencloser.transport.signalwire.dial import is_e164

_CheckName = TelephonyReadinessCheckName
_Result = TelephonyReadinessResult


@dataclass(frozen=True, slots=True)
class Slice3TelephonyConfig:
    """The telephony-side inputs the readiness checker validates (FR-009).

    In production these are loaded from ``config/slice3.toml`` + env (the
    SignalWire credentials presence, source caller-id, and callback-URL
    templates) and the Slice 2 mapping artifact (campaign→persona/runtime and
    Task owner mappings). In the dependency-injectable seam the integration
    tests construct an all-pass instance and break exactly one field per
    FR-009 category to exercise each readiness failure (US3 T041).

    Defaults are an all-pass configuration so US1/US2 runs (which do not yet
    thread a telephony config) keep passing readiness unchanged.
    """

    signalwire_credentials_present: bool = True
    source_caller_id: str | None = "+15555550100"
    status_callback_url_template: str | None = (
        "https://callbacks.example.com/sw/status/{session_id}"
    )
    media_callback_url_template: str | None = "https://callbacks.example.com/sw/media/{session_id}"
    campaign_persona_runtime_mapping_present: bool = True
    task_owner_mapping_present: bool = True


def _url_configured(template: str | None) -> bool:
    """A callback-URL template is configured iff present and carrying the
    ``{session_id}`` placeholder the receiver substitutes (FR-009; the
    Round 4 ``{session_id}``-only stricter validation lands in T110)."""
    return bool(template) and "{session_id}" in template


class TelephonyReadinessChecker:
    """Evaluate the nine FR-009 pre-dial readiness checks for one session."""

    def check(
        self,
        *,
        session_id: str,
        queue_item: QueueItem | None,
        telephony_config: Slice3TelephonyConfig,
        dataverse_metadata_verified: bool,
        eligibility_blocked: bool,
        now: str,
    ) -> TelephonyReadinessReport:
        # ``queue_item`` is None only on the config-only rehearsal path (no
        # Dataverse item loaded); the destination-phone check then fails with an
        # explanatory detail rather than dereferencing a missing item.
        cfg = telephony_config
        checks: list[TelephonyReadinessCheckResult] = []

        def add(
            name: TelephonyReadinessCheckName, ok: bool, detail_ok: str, detail_fail: str
        ) -> None:
            checks.append(
                TelephonyReadinessCheckResult(
                    check_name=name,
                    result=_Result.PASS if ok else _Result.FAIL,
                    detail=detail_ok if ok else detail_fail,
                    checked_at=now,
                )
            )

        add(
            _CheckName.SIGNALWIRE_CREDENTIALS,
            cfg.signalwire_credentials_present,
            "SignalWire credentials present",
            "SignalWire credentials missing (set SIGNALWIRE_PROJECT_ID / API_TOKEN / SIGNING_SECRET)",
        )
        add(
            _CheckName.SOURCE_CALLER_ID_AUTHORIZED,
            is_e164(cfg.source_caller_id),
            "source caller-id configured and E.164",
            "source caller-id missing or not E.164 (config [signalwire].source_caller_id)",
        )
        add(
            _CheckName.DESTINATION_PHONE_E164,
            queue_item is not None and is_e164(queue_item.phone_number),
            "destination phone passes E.164 validation",
            (
                "no Dataverse queue item loaded (config-only rehearsal)"
                if queue_item is None
                else f"destination phone {queue_item.phone_number!r} is missing, blank, "
                "or not E.164 (FR-010)"
            ),
        )
        add(
            _CheckName.STATUS_CALLBACK_URL_CONFIGURED,
            _url_configured(cfg.status_callback_url_template),
            "status callback URL configured",
            "status callback URL missing or lacks the {session_id} placeholder",
        )
        add(
            _CheckName.MEDIA_CALLBACK_URL_CONFIGURED,
            _url_configured(cfg.media_callback_url_template),
            "media callback URL configured",
            "media callback URL missing or lacks the {session_id} placeholder",
        )
        add(
            _CheckName.CAMPAIGN_PERSONA_RUNTIME_MAPPING,
            cfg.campaign_persona_runtime_mapping_present,
            "campaign-to-persona/runtime mapping resolved",
            "campaign is not mapped to a persona/runtime",
        )
        add(
            _CheckName.DATAVERSE_METADATA_VERIFIED,
            dataverse_metadata_verified,
            "Dataverse metadata verified",
            "Dataverse metadata verification failed (run dataverse-verify)",
        )
        add(
            _CheckName.TASK_OWNER_MAPPING_RESOLVED,
            cfg.task_owner_mapping_present,
            "callback / review Task owner mapping resolved",
            "callback or review Task owner/team mapping is missing or invalid",
        )
        add(
            _CheckName.ELIGIBILITY,
            not eligibility_blocked,
            "call-window / DNC / attempt eligibility allows the call",
            "blocked by call-window / DNC / attempt eligibility (Slice 1 six rules)",
        )

        return TelephonyReadinessReport(session_id=session_id, started_at=now, checks=checks)


__all__ = ("Slice3TelephonyConfig", "TelephonyReadinessChecker")
