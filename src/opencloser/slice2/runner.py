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
from typing import Literal

from opencloser.core.clock import Clock, SystemClock
from opencloser.core.orchestrator import QueueItemNotFound, RunReport, process_one_queue_item
from opencloser.crm.dataverse.adapter import DataverseWriteBackAdapter, DataverseWriteBackError
from opencloser.crm.dataverse.client import DataverseClient
from opencloser.crm.dataverse.errors import DataverseError
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
    RunStatus,
    Slice2Config,
    SliceConfig,
)
from opencloser.persona.alf_appointment_setter import ALFAppointmentSetterPersona
from opencloser.persona.base import ConversationFixture, ConversationTurn, Persona
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

# Anchored E.164: leading +, then 1-15 digits.
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
) -> CrmRunReport:
    """Execute exactly one write-enabled Slice 2 run end-to-end.

    `client` is a configured `DataverseClient` (real or fake). The caller is
    responsible for its lifecycle. `conn` is an open SQLite state connection with
    schema applied.
    """
    clk = clock or SystemClock()
    persona = persona or ALFAppointmentSetterPersona()

    # 1) Readiness — load + validate the mapping artifact, then verify live metadata.
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
    translator = MappingTranslator(mapping)
    try:
        report = verify(client, mapping, now_utc_ms=clk.now_utc_ms())
    except (DataverseError, MetadataError) as exc:
        # An unreachable Dataverse (auth failure, 5xx, timeout) or unverifiable
        # metadata at startup is operator-visible-blocked rather than an unhandled
        # exception. The CLI prints the message and exits with the documented
        # `blocked` exit code.
        return CrmRunReport(
            exit_status="blocked",
            message=f"metadata verification failed: {exc}",
        )
    if not report.ok:
        return CrmRunReport(
            exit_status="blocked",
            message="metadata verification failed: " + "; ".join(report.missing),
            metadata_report=report,
        )

    # 2) Load the queue item. Any mapping/option-set/transient failure surfaces as a
    # structured `failed` report instead of an unhandled exception.
    loader = DataverseQueueLoader(client, translator)
    try:
        queue_item = loader.load(selector)
    except (MappingError, QueueLoadError, DataverseError) as exc:
        return CrmRunReport(exit_status="failed", message=f"queue loader error: {exc}")
    if queue_item is None:
        return CrmRunReport(
            exit_status="no-callable-item",
            metadata_report=report,
            message="no callable queue item",
        )

    # 3) FR-034 — non-E.164 phone-quality warning. Recorded into the runner report and
    # the queue-status payload's `queue.last_error` column (via the adapter; see
    # `_compose_last_error`), without changing the exit status.
    runner_warnings: list[DataQualityWarning] = []
    if queue_item.phone_number and not _E164_RE.match(queue_item.phone_number):
        runner_warnings.append(
            DataQualityWarning(
                code="non_e164_phone",
                field="queue.phone",
                message=f"queue item {queue_item.queue_item_id!r} phone is not E.164",
            )
        )

    # 4) Stage the queue row locally so the unchanged orchestrator can read it.
    _stage_queue_item(conn, queue_item)

    # 5) Construct the boundary objects + adapter and call the orchestrator. The
    # conversation-fixture load is inside the try block so a missing or malformed
    # fixture file produces an exit_status=failed report rather than an unhandled
    # exception.
    adapter = DataverseWriteBackAdapter(
        conn=conn,
        client=client,
        translator=translator,
        task_owners=slice2_config.task_owners,
        now_utc_ms=clk.now_utc_ms,
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
    except (DataverseError, DataverseWriteBackError) as exc:
        # A permanent Dataverse write failure mid-run is operator-visible-failed.
        # The adapter has already recorded `writeback_progress.run_status=blocked`
        # with the error before re-raising, so the resume coordinator can pick up
        # in a later slice (US4).
        return CrmRunReport(
            exit_status="failed",
            message=f"dataverse write failed: {exc}",
            warnings=adapter.warnings(),
        )

    # 7) Stamp terminal progress for the resume ledger.
    terminal_status = _terminal_run_status(orchestrator_report)
    adapter.finalize_progress(orchestrator_report.session_id, run_status=terminal_status)

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


def _terminal_run_status(report: RunReport) -> RunStatus:
    if report.final_disposition is Disposition.BLOCKED:
        return RunStatus.BLOCKED
    return RunStatus.COMPLETED


def _stage_queue_item(conn: sqlite3.Connection, queue_item: QueueItem) -> None:
    """Insert or refresh the queue row in local SQLite from the live Dataverse
    snapshot so the unchanged orchestrator's eligibility evaluator reads current
    state (not whatever a prior run last wrote). FK consumers (sessions, etc.)
    keep their references — only the mutable columns are refreshed."""
    existing = store.get_queue_item(conn, queue_item.queue_item_id)
    if existing is None:
        with store.transaction(conn):
            store.insert_queue_item(conn, queue_item)
        return
    with store.transaction(conn):
        store.update_queue_item_status(
            conn,
            queue_item.queue_item_id,
            callable_status=queue_item.callable_status,
            dnc_flag=queue_item.dnc_flag,
            phone_number=queue_item.phone_number,
            timezone=queue_item.timezone,
            attempt_count=queue_item.attempt_count,
        )


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
