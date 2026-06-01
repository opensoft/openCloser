"""T033 — Slice 3 run-report builder + writer (FR-036, research.md §9).

Every Slice 3 invocation (rehearsal AND real-call) produces exactly one
``artifacts/<session_id>/run_report.json``. This module owns the canonical
:class:`~opencloser.models.RunReport` assembly and the on-disk serializer so
the runner (T034), the rehearsal branch (T038), and the readiness gate (T046)
all emit a structurally identical report.

The report deliberately carries NO secrets (SC-018): operator identity,
runtime/model identity (credential-free per FR-035), provider call id, and
per-operation write-back status are the only identifiers it surfaces.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from opencloser.models import (
    Disposition,
    HumanReviewReason,
    OperatorIdentity,
    RealtimeProviderSession,
    RunReport,
    ShadowSTTRunSummary,
    Slice3RunMode,
    TelephonyReadinessCheckResult,
    WriteBackOperationStatus,
)

_RUN_REPORT_FILENAME = "run_report.json"


def build_run_report(
    *,
    session_id: str,
    run_mode: Slice3RunMode,
    operator_current: str,
    operator_original: str | None = None,
    real_provider_call_id: str | None = None,
    persona_version: str,
    runtime_identity: RealtimeProviderSession | None = None,
    final_disposition: Disposition | None = None,
    human_review_reason: HumanReviewReason | None = None,
    blocked_reason: str | None = None,
    telephony_readiness_summary: Sequence[TelephonyReadinessCheckResult] | None = None,
    per_writeback_operation_status: Sequence[WriteBackOperationStatus] | None = None,
    shadow_stt_enabled: bool = False,
    shadow_discrepancy_summary: str = "",
    shadow_lane_truncated: bool = False,
    callbacks_audit_row_count: int = 0,
    conflicting_callbacks_audit_row_count: int = 0,
    rejected_auth_callbacks_count: int = 0,
    started_at: str,
    ended_at: str | None = None,
) -> RunReport:
    """Assemble the FR-036 (Round 2-amended) run report for one session.

    ``operator_original`` is preserved (and surfaced) only on resume when it
    differs from the current operator (Round 2 Q12); a fresh run leaves it
    ``None``. ``per_writeback_operation_status`` MUST already be in emission
    order — on ``do_not_call`` the DNC variant first (Round 2 Q14).
    """
    return RunReport(
        session_id=session_id,
        run_mode=run_mode,
        operator_identity=OperatorIdentity(
            current=operator_current, original=operator_original
        ),
        real_provider_call_id=real_provider_call_id,
        persona_version=persona_version,
        runtime_identity=runtime_identity,
        final_disposition=final_disposition,
        human_review_reason=human_review_reason,
        blocked_reason=blocked_reason,
        telephony_readiness_summary=list(telephony_readiness_summary or []),
        per_writeback_operation_status=list(per_writeback_operation_status or []),
        shadow_stt=ShadowSTTRunSummary(
            enabled=shadow_stt_enabled,
            discrepancy_summary=shadow_discrepancy_summary,
            lane_truncated=shadow_lane_truncated,
        ),
        callbacks_audit_row_count=callbacks_audit_row_count,
        conflicting_callbacks_audit_row_count=conflicting_callbacks_audit_row_count,
        rejected_auth_callbacks_count=rejected_auth_callbacks_count,
        started_at=started_at,
        ended_at=ended_at,
    )


def write_run_report(artifact_dir: str | Path, report: RunReport) -> Path:
    """Serialize ``report`` to ``<artifact_dir>/run_report.json`` and return the path.

    The directory is created if missing. ``pydantic``'s ``model_dump_json``
    renders enums by value (so ``final_disposition`` / ``run_mode`` are plain
    strings) — exactly the shape the FR-036 contract test scans.
    """
    session_dir = Path(artifact_dir)
    session_dir.mkdir(parents=True, exist_ok=True)
    path = session_dir / _RUN_REPORT_FILENAME
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return path


__all__ = ("build_run_report", "write_run_report")
