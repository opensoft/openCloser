"""Exported-artifact writer (FR-023 + research.md §Artifact directory & filenames).

Writes deterministic, sorted-keys, 2-space-indented, UTF-8, LF-ended JSON. Atomic via
``tempfile + os.replace`` so duplicate-event redelivery (FR-019) can re-emit identical
bytes without races.

**Retention contract (FR-035, T041)**:

- Local audit artifacts are retained for **at least 90 days** by default; deployments
  MAY configure longer retention but MUST NOT configure shorter.
- The application **MUST NOT auto-delete** any audit artifact. Pruning is a manual
  operator action — neither this writer nor any other module schedules deletion of
  session artifacts, run reports, or any file under ``<artifact_root>/<session_id>/``.
- The one exception is the FR-030 summary-only transcript sweep
  (``(session_dir / _TRANSCRIPT_FILENAME).unlink(missing_ok=True)``): when redaction
  retention is set to ``summary-only`` the writer removes any stale transcript file
  from an earlier run for the SAME session so PII cannot persist after a policy
  change. This is not an auto-deletion of audit data — it is a per-session privacy
  enforcement at write time, and ``session-result.json`` clears its
  ``transcript_pointer`` to match. Note: the unlink-then-write order is intentional
  and privacy-safe — if ``_write_json_atomic(session_result_path, ...)`` fails after
  the unlink, the worst case is a session-result.json from a prior run advertising
  a now-deleted transcript file (a dangling pointer the operator can spot); the
  next successful run resyncs the pointer.
- Secrets MUST NOT be retained in any local audit artifact (FR-005, FR-035). This is
  asserted by ``tests/contract/test_no_secrets_in_artifacts.py`` (T047), which runs
  a write-enabled flow with distinctive secret env values and greps every produced
  artifact for those values.
- Boundary contract (SC-010 / T040): vendor-specific Dataverse field names MUST NOT
  appear in this module. ``tests/contract/test_boundary_isolation.py`` enforces the
  property across the orchestrator/eligibility/transport/persona boundary modules;
  the writer is permitted to know about ``writeback.json`` / ``task.json`` filenames
  because those carry the Slice 1 CONCEPTUAL contract payloads, not vendor logical
  names.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from opencloser.models import (
    ConflictingEventAuditRecord,
    ExportedEligibilityDecision,
    NormalizedResult,
    TaskPayload,
    WriteBack,
)
from opencloser.redaction.layer import RedactionLayer

_TRANSCRIPT_FILENAME = "transcript.txt"
_SESSION_RESULT_FILENAME = "session-result.json"
_WRITEBACK_FILENAME = "writeback.json"
_TASK_FILENAME = "task.json"
_ELIGIBILITY_DECISION_FILENAME = "eligibility-decision.json"
_CONFLICTING_EVENTS_FILENAME = "conflicting-events.json"
_DRY_RUN_MARKER_FILENAME = "dry-run-marker.json"

# Cached so repeated calls without an explicit layer don't re-compile the built-in
# redaction patterns on every session write.
_DEFAULT_REDACTION_LAYER = RedactionLayer.default()


@dataclass(frozen=True, slots=True)
class ArtifactPaths:
    """The relative paths written for one session."""

    session_dir: Path
    session_result: Path
    writeback: Path
    task: Path | None
    transcript: Path | None
    eligibility_decision: Path
    conflicting_events: Path | None


def write_session_artifacts(
    *,
    artifact_root: str | Path,
    session_id: str,
    normalized_result: NormalizedResult,
    writeback: WriteBack,
    eligibility_decision: ExportedEligibilityDecision,
    transcript_text: str | None = None,
    conflicting_events: list[ConflictingEventAuditRecord] | None = None,
    task: TaskPayload | None = None,
    redaction_layer: RedactionLayer | None = None,
) -> ArtifactPaths:
    """Write all per-session artifacts into ``<artifact_root>/<session_id>/``.

    Each individual file is written atomically (tempfile + ``os.replace``); the set
    of artifacts as a whole is not transactional. Atomicity is per-file, which is
    what duplicate-event redelivery (FR-019) and idempotent re-emission need.

    Transcript text always passes through the configured ``RedactionLayer`` before
    disk write (FR-028..FR-030). When the layer's retention mode is
    ``"summary-only"`` — or no transcript text was supplied — no transcript file
    is written; the exported ``transcript_pointer`` is cleared so the
    session-result never advertises a file that does not exist. Under
    ``"summary-only"`` retention, any pre-existing transcript file from an
    earlier run is removed so idempotent re-emit cannot leave PII on disk.

    See :func:`write_dry_run_marker` for the FR-031 US2 dry-run signal — the
    orchestrator's ``write_session_artifacts`` call is unchanged in dry-run
    (the ``writeback.json`` / ``task.json`` it writes happen to contain planned
    content because the adapter captured planned payloads), and the runner
    calls :func:`write_dry_run_marker` separately after
    ``process_one_queue_item`` returns to flag the session as dry-run.
    """
    session_dir = Path(artifact_root) / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    # Decide retention BEFORE writing session-result, so the exported pointer never
    # advertises a transcript file that the writer is about to skip
    # (contracts/redaction-layer.md §Behavior; FR-030).
    effective_layer = redaction_layer or _DEFAULT_REDACTION_LAYER
    summary_only = (
        transcript_text is not None and effective_layer.retention_mode() == "summary-only"
    )
    transcript_will_be_written = transcript_text is not None and not summary_only
    if not transcript_will_be_written and normalized_result.transcript_pointer is not None:
        normalized_result = normalized_result.model_copy(update={"transcript_pointer": None})

    # FR-030 + FR-019: when no transcript will be written (summary-only retention OR no
    # transcript_text supplied), remove any transcript file from an earlier run BEFORE
    # writing session-result.json. If the unlink fails (locked file / permissions), we
    # raise here without having advertised a null transcript_pointer that would leave
    # the on-disk state both privacy-inconsistent and harder to detect.
    if not transcript_will_be_written:
        (session_dir / _TRANSCRIPT_FILENAME).unlink(missing_ok=True)

    session_result_path = session_dir / _SESSION_RESULT_FILENAME
    _write_json_atomic(session_result_path, normalized_result)

    writeback_path = session_dir / _WRITEBACK_FILENAME
    _write_json_atomic(writeback_path, writeback)

    task_path: Path | None = None
    if task is not None:
        task_path = session_dir / _TASK_FILENAME
        _write_json_atomic(task_path, task)

    transcript_path: Path | None = None
    if transcript_will_be_written:
        transcript_path = session_dir / _TRANSCRIPT_FILENAME
        _write_text_atomic(transcript_path, effective_layer.redact(transcript_text))

    eligibility_path = session_dir / _ELIGIBILITY_DECISION_FILENAME
    _write_json_atomic(eligibility_path, eligibility_decision)

    conflicting_path: Path | None = None
    if conflicting_events:
        conflicting_path = session_dir / _CONFLICTING_EVENTS_FILENAME
        _write_json_atomic(
            conflicting_path,
            _ConflictingEventsArtifact(
                schema_version="slice1-v1",
                session_id=session_id,
                events=conflicting_events,
            ),
        )

    return ArtifactPaths(
        session_dir=session_dir,
        session_result=session_result_path,
        writeback=writeback_path,
        task=task_path,
        transcript=transcript_path,
        eligibility_decision=eligibility_path,
        conflicting_events=conflicting_path,
    )


class _ConflictingEventsArtifact(BaseModel):
    """Container for conflicting-events.json (FR-020 audit log export)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str
    session_id: str
    events: list[ConflictingEventAuditRecord]


class _DryRunMarker(BaseModel):
    """Container for dry-run-marker.json (FR-031 US2 dry-run artifact marker)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "slice2-dry-run-marker-v1"
    session_id: str
    note: str = (
        "This session ran in dry-run mode (FR-031). The writeback.json and task.json "
        "files in this directory contain what a write-enabled run WOULD have sent to "
        "Dataverse; zero create or update operations were issued against the CRM."
    )


def write_dry_run_marker(*, artifact_root: str | Path, session_id: str) -> Path:
    """Write the FR-031 US2 dry-run marker file alongside the session artifacts.

    The Slice 1 orchestrator is unchanged (FR-014), so it writes
    ``writeback.json`` / ``task.json`` with the same filenames in both modes.
    In dry-run those files contain the payloads the adapter CAPTURED (no
    Dataverse writes were issued). This marker makes the dry-run nature
    inspectable at a glance without changing the orchestrator's artifact
    filenames (SC-002, SC-013). The runner calls this AFTER
    ``process_one_queue_item`` returns in dry-run mode.
    """
    session_dir = Path(artifact_root) / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    marker_path = session_dir / _DRY_RUN_MARKER_FILENAME
    _write_json_atomic(marker_path, _DryRunMarker(session_id=session_id))
    return marker_path


def _write_json_atomic(path: Path, model: BaseModel) -> None:
    """Write a Pydantic model as deterministic JSON via tempfile + os.replace."""
    payload = model.model_dump(mode="json")
    serialized = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False)
    _write_bytes_atomic(path, (serialized + "\n").encode("utf-8"))


def _write_text_atomic(path: Path, text: str) -> None:
    # LF line endings, UTF-8, no BOM. Ensure trailing newline.
    if not text.endswith("\n"):
        text = text + "\n"
    _write_bytes_atomic(path, text.encode("utf-8"))


def _write_bytes_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp_name, path)
    except Exception:
        # Best-effort cleanup if the rename never happened.
        if Path(tmp_name).exists():
            os.unlink(tmp_name)
        raise


def _serialize_any(value: Any) -> str:  # pragma: no cover - convenience for tests
    """Helper for callers that want a deterministic JSON string of an arbitrary value."""
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False)
