"""Mock CRM Write-back Adapter ABC — FR-033 module boundary #5 (write-back side).

Contract: see specs/001-mock-call-mock-crm/contracts/crm-writeback.md
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from opencloser.models import (
    PhoneCallActivityPayload,
    QueueStatusUpdatePayload,
    TaskPayload,
    WriteBack,
)


@runtime_checkable
class WriteBackAdapter(Protocol):
    """FR-016 conceptual contract that the future Dataverse adapter will satisfy.

    Marked ``@runtime_checkable`` so ``isinstance(adapter, WriteBackAdapter)`` works —
    this is the Slice 1 runtime enforcement of FR-033's module-boundary contract
    (spec.md Round 2 Q23: "Python ABCs/Protocols in base.py are the runtime enforcement").
    """

    def emit_phone_call_activity(
        self, payload: PhoneCallActivityPayload
    ) -> None:  # pragma: no cover - protocol
        ...

    def emit_queue_status_update(
        self, payload: QueueStatusUpdatePayload
    ) -> None:  # pragma: no cover - protocol
        ...

    def emit_task(self, payload: TaskPayload) -> None:  # pragma: no cover - protocol
        ...

    def build_writeback(self, session_id: str) -> WriteBack:  # pragma: no cover - protocol
        """Return the assembled in-memory `WriteBack` aggregate for one session (FR-015)."""
        ...
