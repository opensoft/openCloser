"""Mock CRM Write-back Adapter ABC — FR-033 module boundary #5 (write-back side).

Contract: see specs/001-mock-call-mock-crm/contracts/crm-writeback.md
"""

from __future__ import annotations

from typing import Protocol

from opencloser.models import (
    PhoneCallActivityPayload,
    QueueStatusUpdatePayload,
    TaskPayload,
)


class WriteBackAdapter(Protocol):
    """FR-016 conceptual contract that the future Dataverse adapter will satisfy."""

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
