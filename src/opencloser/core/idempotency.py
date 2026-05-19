"""FR-019 idempotency-key composition and duplicate-detection helpers.

The orchestrator wraps every state mutation in a ``try_record_idempotency_key`` call.
UNIQUE-constraint violation on the composite PK is the signal that the mutation has
already been applied and MUST be a no-op.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from opencloser.models import WriteBackKind
from opencloser.state import store


@dataclass(frozen=True, slots=True)
class IdempotencyKey:
    """FR-019 tuple `(session_id, mock_provider_call_id, event_id, write_back_kind)`."""

    session_id: str
    mock_provider_call_id: str | None
    event_id: str | None
    write_back_kind: WriteBackKind

    def as_tuple(self) -> tuple[str, str, str, str]:
        return (
            self.session_id,
            self.mock_provider_call_id or "",
            self.event_id or "",
            self.write_back_kind.value,
        )


def compute_key(
    *,
    session_id: str,
    mock_provider_call_id: str | None,
    event_id: str | None,
    write_back_kind: WriteBackKind,
) -> IdempotencyKey:
    return IdempotencyKey(
        session_id=session_id,
        mock_provider_call_id=mock_provider_call_id,
        event_id=event_id,
        write_back_kind=write_back_kind,
    )


def record_or_skip(conn: sqlite3.Connection, key: IdempotencyKey, *, applied_at: str) -> bool:
    """Return True if the key is fresh and the caller should proceed; False if duplicate."""
    return store.try_record_idempotency_key(
        conn,
        session_id=key.session_id,
        mock_provider_call_id=key.mock_provider_call_id,
        event_id=key.event_id,
        write_back_kind=key.write_back_kind.value,
        applied_at=applied_at,
    )
