"""Slice 2 write-enabled run coordinator (FR-002, FR-007, FR-014, FR-031-FR-034).

Wraps the **unchanged** Slice 1 orchestrator (FR-014). Per write-enabled run:

1. Validates readiness — Slice 2 config, Dataverse secrets, mapping artifact, and the
   live metadata-verification report (FR-002, FR-007).
2. Loads exactly one queue item via `DataverseQueueLoader` — an empty queue is a
   clean no-op (FR-009).
3. Stages the loaded `QueueItem` in local SQLite (the orchestrator owns sessions and
   reads queue rows from local state — slice 1 contract unchanged).
4. Constructs the boundary objects, including `DataverseWriteBackAdapter`, and runs
   `process_one_queue_item` (FR-014).
5. Records the FR-034 non-E.164 phone data-quality warning into the runner report
   and the queue-status payload without changing the exit status.
6. Stamps `writeback_progress.run_status` with the terminal status (FR-023).

See specs/002-mock-call-real-crm/contracts/cli-slice2.md.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from re import error as re_error
from typing import Literal

from pydantic import ValidationError

from opencloser.artifacts.writer import write_dry_run_marker
from opencloser.core.clock import Clock, SystemClock
from opencloser.core.orchestrator import QueueItemNotFound, RunReport, process_one_queue_item
from opencloser.crm.dataverse.adapter import (
    DataverseWriteBackAdapter,
    DataverseWriteBackError,
    QueueConflictError,
)
from opencloser.crm.dataverse.client import DataverseClient
from opencloser.crm.dataverse.errors import (
    DataverseError,
    PermanentDataverseError,
    TransientDataverseError,
)
from opencloser.crm.dataverse.mapping import MappingError, MappingTranslator, load_mapping
from opencloser.crm.dataverse.metadata import MetadataError, verify
from opencloser.crm.dataverse.queue_loader import (
    DataverseQueueLoader,
    QueueLoadError,
    QueueSelector,
)
from opencloser.eligibility.evaluator import BuiltinEligibilityEvaluator
from opencloser.models import (
    DataQualityWarning,
    Disposition,
    MetadataVerificationReport,
    QueueItem,
    RunMode,
    RunStatus,
    Slice2Config,
    SliceConfig,
)
from opencloser.persona.alf_appointment_setter import ALFAppointmentSetterPersona
from opencloser.persona.base import ConversationFixture, ConversationTurn, Persona
from opencloser.redaction.layer import RedactionLayer
from opencloser.state import store
from opencloser.transport.mock import FixtureDrivenTransport

# CLI exit-status names per contracts/cli-slice2.md.
ExitStatus = Literal[
    "completed",
    "blocked",
    "no-callable-item",
    "resume_needed",
    "failed",
]

# Anchored E.164: leading `+`, then a non-zero leading digit, then 1-14 more
# digits (so 2-15 digits total). The minimum-two requirement comes from the
# mandatory `[1-9]` prefix; in practice every real-world E.164 number has at
# least a country code plus a subscriber digit.
_E164_RE = re.compile(r"^\+[1-9]\d{1,14}$")


@dataclass
class CrmRunReport:
    """The runner's exit report — superset of the orchestrator `RunReport`."""

    exit_status: ExitStatus
    session_id: str | None = None
    final_disposition: Disposition | None = None
    artifact_dir: Path | None = None
    queue_item_id: str | None = None
    metadata_report: MetadataVerificationReport | None = None
    warnings: list[DataQualityWarning] = field(default_factory=list)
    message: str | None = None


@dataclass(frozen=True)
class _ReadinessResult:
    translator: MappingTranslator
    metadata_report: MetadataVerificationReport
    redaction_layer: RedactionLayer


_DRY_RUN_TOLERABLE_AUTH_STATUS_CODES: frozenset[int] = frozenset({400, 401})


def _is_dry_run_tolerable_verify_failure(exc: Exception) -> bool:
    """Per `contracts/metadata-discovery-verification.md` §5 + spec §Edge Cases
    "Dry-run requested but write credentials are absent", dry-run readiness
    tolerates a NARROW set of `verify()` failures that correspond to
    "no working credentials" or "environment temporarily unreachable":

    1. A `PermanentDataverseError` with HTTP 400 (Microsoft Entra
       `invalid_request` for malformed tenant/client when the operator has
       placeholder secrets) or HTTP 401 (`invalid_client` / bad
       client_secret). Both are the "missing/invalid write credentials"
       scenario the spec carves out (Codex PR #7 round-4 P1: a placeholder
       tenant typically returns 400, not 401, so 401-only was too narrow).
    2. A `TransientDataverseError` — network unreachable, 5xx, timeout. The
       runtime cannot determine whether the configured metadata is valid;
       dry-run should not fail-hard on environmental flakiness (this is a
       deliberate liberalization vs. strictly the contract wording — a
       transient 5xx blocking dry-run rehearsal is worse UX than letting
       the operator notice their environment is flaky and retry).

    Anything else — 403/permission regression, 404 entity not found, a
    `MetadataError` from a missing-mapping read — is a REAL verification
    failure that must block dry-run too, so an operator does not approve a
    rehearsal whose write-enabled counterpart would immediately fail
    (Codex PR #7 round-3 P1).
    """
    if isinstance(exc, TransientDataverseError):
        return True
    return (
        isinstance(exc, PermanentDataverseError)
        and exc.status_code in _DRY_RUN_TOLERABLE_AUTH_STATUS_CODES
    )


def run_one_crm_item(
    selector: QueueSelector,
    *,
    transport_fixture: Path,
    conversation_fixture: Path | None,
    slice1_config: SliceConfig,
    slice2_config: Slice2Config,
    client: DataverseClient,
    conn: sqlite3.Connection,
    clock: Clock | None = None,
    persona: Persona | None = None,
    run_mode: RunMode = RunMode.WRITE_ENABLED,
) -> CrmRunReport:
    """Execute exactly one Slice 2 run end-to-end.

    `client` is a configured `DataverseClient` (real or fake). The caller is
    responsible for its lifecycle. `conn` is an open SQLite state connection with
    schema applied.

    ``run_mode`` selects between **write-enabled** (the default — performs live
    metadata verification, claims/mutates the Dataverse queue item, and POSTs /
    PATCHes the write-back records) and **dry-run** (FR-031 — still calls live
    ``verify()`` to surface real mapping/option-set gaps per
    ``contracts/metadata-discovery-verification.md`` §5, but tolerates a narrow
    set of failures (``TransientDataverseError`` + 401 PermanentDataverseError)
    so an environment without write credentials does not block the rehearsal
    per spec §Edge Cases. Never mutates the Dataverse queue item per FR-010,
    constructs the adapter with ``dry_run=True`` so every ``emit_*`` captures
    the planned payload without issuing any POST / PATCH (and skips the GET
    pre-queries within ``emit_*``; the queue load itself still uses GETs via
    ``DataverseQueueLoader``), and writes the FR-031 dry-run marker artifact
    alongside the orchestrator's session artifacts). The CLI default is
    dry-run (FR-031, SC-013); the write-enabled path requires an explicit
    ``--write`` flag.
    """
    clk = clock or SystemClock()
    persona = persona or ALFAppointmentSetterPersona()
    is_dry_run = run_mode is RunMode.DRY_RUN

    version_report = _persona_version_mismatch_report(persona, slice1_config)
    if version_report is not None:
        return version_report

    readiness = _verify_readiness(slice2_config, client, clk, dry_run=is_dry_run)
    if isinstance(readiness, CrmRunReport):
        return readiness
    translator = readiness.translator
    report = readiness.metadata_report
    redaction_layer = readiness.redaction_layer

    queue_item_result = _load_dataverse_queue_item(
        selector=selector,
        client=client,
        translator=translator,
        slice2_config=slice2_config,
        metadata_report=report,
    )
    if isinstance(queue_item_result, CrmRunReport):
        return queue_item_result
    queue_item = queue_item_result

    # 3) FR-034 — non-E.164 phone-quality warning. Recorded into the runner report and
    # the queue-status payload's `queue.last_error` column (via the adapter; see
    # `_compose_last_error`), without changing the exit status.
    runner_warnings = _phone_quality_warnings(queue_item)

    # 4) Stage the queue row locally so the unchanged orchestrator can read it.
    _stage_queue_item(conn, queue_item)

    # 5) Construct the boundary objects + adapter and call the orchestrator. The
    # conversation-fixture load is inside the try block so a missing or malformed
    # fixture file produces an exit_status=failed report rather than an unhandled
    # exception. The adapter stages failure markers in memory; the runner
    # flushes them AFTER catching the emit_* exception (when the orchestrator's
    # rolling-back transaction has released SQLite's write lock).
    adapter = DataverseWriteBackAdapter(
        conn=conn,
        client=client,
        translator=translator,
        task_owners=slice2_config.task_owners,
        now_utc_ms=clk.now_utc_ms,
        dry_run=is_dry_run,
        # T045: pass the loaded queue snapshot so the adapter can detect
        # mid-run human changes (FR-003 + FR-021) before the final PATCH.
        # Skipped for dry-run because dry-run never PATCHes anyway, and
        # the conflict-detection GET would defeat the FR-031 "zero write"
        # guarantee's narrow scoping if we issued it without need.
        queue_snapshot=None if is_dry_run else queue_item,
    )
    for warning in runner_warnings:
        adapter.add_warning(warning)

    transport_dir = transport_fixture.parent
    transport_fixture_id = transport_fixture.stem
    try:
        conversation = (
            _load_conversation_fixture(conversation_fixture) if conversation_fixture else None
        )
        orchestrator_report = process_one_queue_item(
            queue_item.queue_item_id,
            conn=conn,
            config=slice1_config,
            eligibility=BuiltinEligibilityEvaluator(),
            transport=FixtureDrivenTransport(transport_dir),
            persona=persona,
            crm=adapter,
            conversation_fixture=conversation,
            transport_fixture_id=transport_fixture_id,
            clock=clk,
            redaction_layer=redaction_layer,
        )
    except QueueItemNotFound as exc:
        return CrmRunReport(exit_status="failed", message=f"queue item not found locally: {exc}")
    except (ValueError, OSError) as exc:
        # Malformed transport/conversation fixture, missing file. The orchestrator
        # pre-validates allow-path inputs before any session row is created, so no
        # attempt is consumed (FR-019/FR-020 spirit).
        return CrmRunReport(
            exit_status="failed",
            message=str(exc),
            warnings=adapter.warnings(),
        )
    except (DataverseError, DataverseWriteBackError, MappingError) as exc:
        # A Dataverse write failure mid-run, or a missing/invalid mapping entry
        # surfaced by the adapter (e.g. `primary_id` not set), is
        # operator-visible-failed. The orchestrator's `with
        # store.transaction(conn)` around the failing emit_* has already
        # rolled back; the SQLite write lock is free again, so we can now
        # safely persist the failure markers the adapter staged.
        #
        # Distinguish three failure modes for the resume ledger + exit status:
        # 1. TransientDataverseError (retry budget exhausted) → RESUME_NEEDED,
        #    exit_status="resume_needed" (FR-023). The client's `_request`
        #    retries on transient errors until budget exhausted then re-raises.
        # 2. QueueConflictError (T045 — human change between claim and write)
        #    → BLOCKED, exit_status="blocked". A conflict is a workflow
        #    state divergence requiring human reconciliation; retry won't
        #    recover. Spec §Edge Cases "Dataverse queue item changed by a
        #    human between claim and write-back".
        # 3. Other DataverseError / DataverseWriteBackError / MappingError
        #    → BLOCKED, exit_status="failed".
        if isinstance(exc, QueueConflictError):
            failure_run_status = RunStatus.BLOCKED
            failure_exit_status = "blocked"
        elif isinstance(exc, TransientDataverseError):
            failure_run_status = RunStatus.RESUME_NEEDED
            failure_exit_status = "resume_needed"
        else:
            failure_run_status = RunStatus.BLOCKED
            failure_exit_status = "failed"
        # Capture session ids BEFORE flush clears the pending queue (Copilot
        # PR #9 round-2 P1: operators need the session id to invoke
        # `run-crm --resume <session-id>` — the orchestrator's caught
        # exception doesn't carry it, but the adapter staged it in
        # `_record_failure`).
        failure_session_ids = adapter.pending_failure_session_ids()
        adapter.flush_pending_failures(failure_run_status=failure_run_status)
        return CrmRunReport(
            exit_status=failure_exit_status,
            session_id=failure_session_ids[0] if failure_session_ids else None,
            queue_item_id=queue_item.queue_item_id,
            metadata_report=report,
            message=(
                # Conflict gets a distinct prefix so operators can grep
                # for it in run reports without having to inspect the
                # underlying exception type.
                f"queue conflict — manual reconciliation required: {exc}"
                if isinstance(exc, QueueConflictError)
                else f"dataverse write failed: {exc}"
            ),
            warnings=adapter.warnings(),
        )

    # 6) Stamp terminal progress for the resume ledger. In dry-run this is a
    # no-op inside the adapter (no Dataverse write happened, no
    # `writeback_progress` row to record).
    terminal_status = _terminal_run_status(orchestrator_report)
    adapter.finalize_progress(orchestrator_report.session_id, run_status=terminal_status)

    # 7) FR-031 dry-run marker — the Slice 1 orchestrator writes the planned
    # `writeback.json` / `task.json` under their usual filenames (its writer
    # call is unchanged per FR-014), so an inspector cannot tell from the
    # filenames alone that no Dataverse write was issued. The marker file
    # makes the dry-run nature unambiguous (SC-002, SC-013). A filesystem
    # failure here MUST NOT crash the run — convert to a structured `failed`
    # report so the operator sees a stable exit-status (Codex PR #7 round-3:
    # don't introduce a new uncaught-exception path with the marker step).
    if is_dry_run and orchestrator_report.artifact_dir is not None:
        try:
            write_dry_run_marker(
                artifact_root=orchestrator_report.artifact_dir.parent,
                session_id=orchestrator_report.session_id,
            )
        except OSError as exc:
            return CrmRunReport(
                exit_status="failed",
                session_id=orchestrator_report.session_id,
                final_disposition=orchestrator_report.final_disposition,
                artifact_dir=orchestrator_report.artifact_dir,
                queue_item_id=queue_item.queue_item_id,
                metadata_report=report,
                warnings=adapter.warnings(),
                message=f"dry-run marker write failed: {exc}",
            )

    exit_status: ExitStatus = (
        "blocked" if orchestrator_report.final_disposition is Disposition.BLOCKED else "completed"
    )
    return CrmRunReport(
        exit_status=exit_status,
        session_id=orchestrator_report.session_id,
        final_disposition=orchestrator_report.final_disposition,
        artifact_dir=orchestrator_report.artifact_dir,
        queue_item_id=queue_item.queue_item_id,
        metadata_report=report,
        warnings=adapter.warnings(),
    )


def _persona_version_mismatch_report(
    persona: Persona, slice1_config: SliceConfig
) -> CrmRunReport | None:
    # Persona-version gate — the orchestrator hands `persona.version` to every
    # write-back payload (`PhoneCallActivityPayload`, `TaskPayload`), so running
    # against a mismatched persona silently produces records tagged with a
    # different version than the operator configured. The Slice 1 CLI's run-one
    # checks this and the Slice 2 runner mirrors that fail-fast behavior.
    if persona.version == slice1_config.persona.version:
        return None
    return CrmRunReport(
        exit_status="blocked",
        message=(
            f"persona version mismatch: slice1.toml requires "
            f"{slice1_config.persona.version!r} but the running persona is "
            f"{persona.version!r}"
        ),
    )


def _verify_readiness(
    slice2_config: Slice2Config,
    client: DataverseClient,
    clk: Clock,
    *,
    dry_run: bool = False,
) -> _ReadinessResult | CrmRunReport:
    """FR-007 startup/readiness validation (T028, T029a, T029b).

    Validation order (each gate blocks before the next, all produce
    operator-visible messages per spec §Definitions §"Operator-visible"):

    1. **Mapping artifact**: file present, valid schema, ``_meta.approved == true``.
    2. **Redaction policy** (T028): the configured ``[redaction]`` patterns
       compile and the retention mode is valid (spec §Edge Cases "Malformed
       redaction policy"). Validated for BOTH dry-run and write-enabled
       because the redaction layer is default-on in both modes (FR-028).
    3. **Live metadata verification** (T029a): for write-enabled, runs
       ``verify()`` and blocks on any missing entity / field / option-set
       (FR-002). Dry-run also calls ``verify()`` per
       ``contracts/metadata-discovery-verification.md`` §5 but tolerates
       auth-401/400 and transient failures per spec §Edge Cases "Dry-run
       requested but write credentials are absent".
    4. **Idempotency-key fields** (T029a, SC-015): the mapping MUST declare
       both ``phone_call.idempotency_key`` and ``task.idempotency_key``. An
       unmapped key field is explicitly surfaced here rather than failing
       deep inside the adapter at write time.

    Dataverse-unreachable-at-start (T029b operational gate) is handled by
    the ``verify()`` exception path: a transient/auth failure on the
    startup ``verify()`` call produces a blocked report (write-enabled) or
    a tolerated placeholder (dry-run + 401/400/transient).

    Configured-campaign-not-found (T029b operational gate) is currently
    indistinguishable from FR-009 empty-queue-no-op because the
    queue-loader's campaign filter is opaque to mapping-time validation
    (the campaign value may be a free-form string OR a GUID lookup-target
    depending on the mapping). Tracked as a known gap; see
    ``test_us3_metadata_block.py`` for the documented behavior.
    """
    # 1) Mapping artifact load + approval gate.
    try:
        mapping = load_mapping(slice2_config.dataverse.mapping_artifact)
    except MappingError as exc:
        return CrmRunReport(exit_status="blocked", message=f"mapping artifact error: {exc}")
    if not mapping.meta.approved:
        return CrmRunReport(
            exit_status="blocked",
            message=(
                f"mapping artifact {slice2_config.dataverse.mapping_artifact!r} is not approved; "
                "re-run `discover-crm` and have a reviewer flip _meta.approved to true"
            ),
        )

    # 2) T028 — redaction-policy validation. Default-on in both modes
    # (FR-028); a malformed regex MUST fail readiness before any transcript
    # write, session creation, or attempt increment (spec §Edge Cases
    # "Malformed redaction policy"). The constructed layer is kept and
    # threaded to `process_one_queue_item` below so operator-configured
    # patterns/retention are actually applied during artifact export.
    try:
        redaction_layer = RedactionLayer.from_config(slice2_config.redaction)
    except (ValueError, re_error) as exc:
        return CrmRunReport(
            exit_status="blocked",
            message=f"redaction policy invalid: {exc}",
        )

    # 3) T029a + SC-015 — explicit idempotency-key field check. Pure mapping
    # lookup (no Dataverse), so it runs BEFORE `verify()` to ensure both
    # write-enabled AND the dry-run-tolerated `verify()` failure path enforce
    # SC-015 ("100% of the time when the mapped idempotency-key field for
    # Phone Call activity or Task cannot be verified"). Without this ordering,
    # a dry-run with missing creds AND a missing key-field mapping would
    # silently pass.
    missing_keys = [
        key for key in ("phone_call.idempotency_key", "task.idempotency_key")
        if key not in mapping.fields
    ]
    if missing_keys:
        return CrmRunReport(
            exit_status="blocked",
            message=(
                "idempotency-key field(s) not mapped: "
                f"{', '.join(missing_keys)} — SC-015 requires every "
                "write-enabled run to verify these key fields as real "
                "Dataverse fields. Add them to "
                f"{slice2_config.dataverse.mapping_artifact!r} and re-run "
                "`discover-crm`."
            ),
        )

    translator = MappingTranslator(mapping)
    try:
        report = verify(client, mapping, now_utc_ms=clk.now_utc_ms())
    except (DataverseError, MetadataError) as exc:
        if dry_run and _is_dry_run_tolerable_verify_failure(exc):
            # spec §Edge Cases "Dry-run requested but write credentials are
            # absent" + contracts/metadata-discovery-verification.md §5:
            # dry-run still runs `verify()` AND surfaces gaps; ONLY missing
            # write credentials (auth 401) and pure connectivity failures
            # (`TransientDataverseError`) are tolerated. A 403 / 404 / real
            # `MetadataError` (missing mapping) MUST still block dry-run
            # (Codex PR #7 round-3 P1: a 403 on EntityDefinitions while
            # queue reads still work is a real verification gap, not a
            # missing-credentials story).
            return _ReadinessResult(
                translator=translator,
                metadata_report=MetadataVerificationReport(
                    ok=True,
                    missing=[],
                    drift=[],
                    checked_at=clk.now_utc_ms(),
                ),
                redaction_layer=redaction_layer,
            )
        # All other paths (write-enabled, OR dry-run with a non-tolerable
        # error) are operator-visible-blocked rather than an unhandled
        # exception. The CLI prints the message and exits with the documented
        # `blocked` exit code.
        return CrmRunReport(
            exit_status="blocked",
            message=f"metadata verification failed: {exc}",
        )
    if not report.ok:
        # Real metadata gap (missing fields / option sets / etc.) — blocks BOTH
        # modes per contracts/metadata-discovery-verification.md §5 (dry-run
        # "still runs `verify` and surfaces gaps").
        return CrmRunReport(
            exit_status="blocked",
            message="metadata verification failed: " + "; ".join(report.missing),
            metadata_report=report,
        )

    return _ReadinessResult(
        translator=translator, metadata_report=report, redaction_layer=redaction_layer
    )


def _load_dataverse_queue_item(
    *,
    selector: QueueSelector,
    client: DataverseClient,
    translator: MappingTranslator,
    slice2_config: Slice2Config,
    metadata_report: MetadataVerificationReport,
) -> QueueItem | CrmRunReport:
    # 2) Load the queue item. Any mapping/option-set/transient failure surfaces as a
    # structured `failed` report instead of an unhandled exception. `ValidationError`
    # is included because `loader.load(...)` constructs a `QueueItem` from the
    # Dataverse row, and a schema-corrupted row (e.g. a negative `attempt_count`
    # the CHECK clause would also reject) surfaces from there.
    loader = DataverseQueueLoader(
        client,
        translator,
        callable_status=slice2_config.dataverse.callable_status,
    )
    try:
        queue_item = loader.load(selector)
    except (MappingError, QueueLoadError, DataverseError, ValidationError) as exc:
        return CrmRunReport(exit_status="failed", message=f"queue loader error: {exc}")
    if queue_item is None:
        return CrmRunReport(
            exit_status="no-callable-item",
            metadata_report=metadata_report,
            message="no callable queue item",
        )
    return queue_item


def _phone_quality_warnings(queue_item: QueueItem) -> list[DataQualityWarning]:
    if not queue_item.phone_number or _E164_RE.match(queue_item.phone_number):
        return []
    return [
        DataQualityWarning(
            code="non_e164_phone",
            field="queue.phone",
            message=f"queue item {queue_item.queue_item_id!r} phone is not E.164",
        )
    ]


def _terminal_run_status(report: RunReport) -> RunStatus:
    if report.final_disposition is Disposition.BLOCKED:
        return RunStatus.BLOCKED
    return RunStatus.COMPLETED


def _stage_queue_item(conn: sqlite3.Connection, queue_item: QueueItem) -> None:
    """Insert or refresh the queue row in local SQLite from the live Dataverse
    snapshot so the unchanged orchestrator's eligibility evaluator reads current
    state (not whatever a prior run last wrote). FK consumers (sessions, etc.)
    keep their references — only the mutable columns are refreshed.

    On refresh, every mutable column is overwritten — including null clears
    (Dataverse may legitimately clear `phone_number`/`timezone`). A `None` from
    the live snapshot must mean "the cell is now empty", not "leave the stale
    local value alone"."""
    existing = store.get_queue_item(conn, queue_item.queue_item_id)
    if existing is None:
        with store.transaction(conn):
            store.insert_queue_item(conn, queue_item)
        return
    with store.transaction(conn):
        store.replace_queue_item_mutable_fields(conn, queue_item)


def _load_conversation_fixture(path: Path) -> ConversationFixture:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"conversation fixture {path.name!r} is not a JSON object")
    turns: list[ConversationTurn] = []
    for t in raw.get("turns", []):
        if not isinstance(t, dict) or "role" not in t or "text" not in t:
            raise ValueError(
                f"conversation fixture {path.name!r}: every turn needs 'role' and 'text'"
            )
        turns.append(ConversationTurn(role=t["role"], text=t["text"]))
    return ConversationFixture(
        fixture_id=raw.get("fixture_id", path.stem),
        expected_disposition=raw.get("expected_disposition", ""),
        queue_item_ref=raw.get("queue_item_ref", ""),
        turns=turns,
        expected_extraction=raw.get("expected_extraction", {}),
    )


__all__ = (
    "CrmRunReport",
    "ExitStatus",
    "run_one_crm_item",
)
