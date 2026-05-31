"""Slice 3 — rejected-by-authentication audit log (FR-008 + Round 2 Q9).

This module exposes the ``RejectedAuthCallbackLog`` surface the SignalWire
transport adapter calls when an inbound callback fails HMAC-SHA256 signature
verification. The log is **distinct** from ``CallbacksAuditLog`` (which
records duplicates and out-of-order callbacks) so attempted-forgery signals
are clearly separable from benign delivery anomalies (contract:
``specs/003-real-call-real-crm/contracts/rejected-auth-audit-log.md``).

Stub module — concrete writer lands in T032. Per T013 Q5 the bodies raise
``NotImplementedError`` so the T013b contract tests fail at assertion time
with a clear "expected behavior, got NotImplementedError" message.

What MUST NOT be stored (FR-035, SC-018, Round 2 Q9):

- The HMAC-SHA256 verification secret.
- The failed signature value.
- The callback body content (defense in depth against reflected-payload
  leakage).
- Any other credential string.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


class RejectedAuthCallbackLog:
    """Append-only audit log for callbacks that failed signature verification.

    Implements both the JSONL artifact surface and the SQLite mirror per
    ``contracts/rejected-auth-audit-log.md``. The SQLite mirror exists so
    ``count_for_session`` is O(1) for the run report (FR-036).

    Per T013b TDD red: bodies raise ``NotImplementedError`` until T032 lands.
    """

    def __init__(self, *, artifacts_root: Path, db_path: Path) -> None:
        self._artifacts_root = artifacts_root
        self._db_path = db_path

    def record(
        self,
        *,
        received_at: datetime,
        session_id: str | None,
        source_metadata: dict[str, str],
        http_status: int = 401,
    ) -> None:
        """Append one rejection row to both the JSONL artifact and the
        SQLite mirror.

        - ``session_id`` MAY be ``None`` for forged callbacks that cannot be
          associated with any known session — these land in
          ``artifacts/_unassociated/rejected_auth_callbacks.jsonl``.
        - ``source_metadata`` is a JSON object of provider-supplied source
          identifiers / IP-level metadata where available.
        - ``http_status`` MUST be ``401`` (the SQLite ``CHECK`` constraint
          enforces this on the storage side).

        The method MUST NOT accept the signing secret or the callback body
        as parameters; the call site is responsible for never passing them.
        """

        raise NotImplementedError("T032 — rejected-auth log writer not yet implemented")  # pragma: no cover

    def count_for_session(self, session_id: str) -> int:
        """Return the count of rejected-auth callbacks for the named session.

        Surfaced as ``rejected_auth_callbacks_count`` in the run report per
        FR-036 so operators can detect attempted forgeries.
        """

        raise NotImplementedError("T032 — rejected-auth log reader not yet implemented")  # pragma: no cover
