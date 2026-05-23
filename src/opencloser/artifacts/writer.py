"""Exported-artifact writer (FR-023 + research.md §Artifact directory & filenames).

Writes deterministic, sorted-keys, 2-space-indented, UTF-8, LF-ended JSON. Atomic via
``tempfile + os.replace`` so duplicate-event redelivery (FR-019) can re-emit identical
bytes without races.
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
    """Write all per-session artifacts into ``<artifact_root>/<session_id>/`` atomically.

    Transcript text always passes through the configured ``RedactionLayer`` before disk
    write (FR-028..FR-030). When the layer's retention mode is ``"summary-only"``, no
    transcript file is written; the session-result summary and the rest of the Slice 1
    artifact contract are preserved.
    """
    session_dir = Path(artifact_root) / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    session_result_path = session_dir / _SESSION_RESULT_FILENAME
    _write_json_atomic(session_result_path, normalized_result)

    writeback_path = session_dir / _WRITEBACK_FILENAME
    _write_json_atomic(writeback_path, writeback)

    task_path: Path | None = None
    if task is not None:
        task_path = session_dir / _TASK_FILENAME
        _write_json_atomic(task_path, task)

    transcript_path: Path | None = None
    if transcript_text is not None:
        effective_layer = redaction_layer or RedactionLayer.default()
        if effective_layer.retention_mode() == "full":
            transcript_path = session_dir / _TRANSCRIPT_FILENAME
            _write_text_atomic(transcript_path, effective_layer.redact(transcript_text))
        # else summary-only retention (FR-030): no transcript file is written.

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
