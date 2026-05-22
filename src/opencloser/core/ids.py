"""ID generators (FR-007: globally-unique mock_provider_call_id; FR-019 audit identifiers)."""

from __future__ import annotations

from uuid import uuid4


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def new_session_id() -> str:
    return _new_id("ses")


def new_mock_provider_call_id() -> str:
    """FR-007 — globally unique across all sessions in local state."""
    return _new_id("call")


def new_decision_id() -> str:
    return _new_id("dec")


def new_task_id() -> str:
    return _new_id("task")


def new_audit_id() -> str:
    return _new_id("audit")
