"""Slice 3 — rejected-by-authentication audit log (FR-008 + Round 2 Q9).

This module exposes the ``RejectedAuthCallbackLog`` surface the SignalWire
transport adapter calls when an inbound callback fails HMAC-SHA256 signature
verification. The log is **distinct** from ``CallbacksAuditLog`` (which
records duplicates and out-of-order callbacks) so attempted-forgery signals
are clearly separable from benign delivery anomalies (contract:
``specs/003-real-call-real-crm/contracts/rejected-auth-audit-log.md``).

T032 (2026-06-01): concrete writer. Records to both
``artifacts/<session_id>/rejected_auth_callbacks.jsonl`` (or
``artifacts/_unassociated/...`` when the callback matches no known session) and
the ``rejected_auth_callbacks`` SQLite table (so ``count_for_session`` is O(1)
for the FR-036 run report).

What MUST NOT be stored (FR-035, SC-018, Round 2 Q9):

- The HMAC-SHA256 verification secret, the failed signature value, and the
  callback body content. ``record`` never accepts the secret or body; in
  addition, ``source_metadata`` is **allowlist-scrubbed** to a fixed set of
  source-identifier keys so a buggy call site cannot smuggle body/secret
  content through it (defense in depth).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

_JSONL_NAME = "rejected_auth_callbacks.jsonl"
_UNASSOCIATED_DIR = "_unassociated"

# Allowlist of source-metadata keys that are safe to persist (provider-supplied
# source identifiers / IP-level metadata per the contract). Any other key — e.g.
# an accidentally-echoed callback body — is dropped before storage (Round 2 Q9).
_SAFE_SOURCE_METADATA_KEYS: frozenset[str] = frozenset({
    "remote_addr",
    "remote_port",
    "sw_source",
    "user_agent",
    "forwarded_for",
    "x_forwarded_for",
})

# CREATE-IF-NOT-EXISTS form of the schema.sql ``rejected_auth_callbacks`` table,
# so the writer works against a DB that has not had the full schema applied
# (e.g. the transport adapter's default state DB). Mirrors state/schema.sql.
_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS rejected_auth_callbacks (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    received_at          TEXT NOT NULL,
    session_id           TEXT,
    source_metadata_json TEXT NOT NULL,
    http_status          INTEGER NOT NULL CHECK (http_status = 401)
);
CREATE INDEX IF NOT EXISTS idx_rejected_auth_session
    ON rejected_auth_callbacks(session_id);
"""


def _scrub_source_metadata(source_metadata: dict[str, str]) -> dict[str, str]:
    """Drop any key not on the safe allowlist (defense in depth — Round 2 Q9)."""
    return {k: v for k, v in source_metadata.items() if k in _SAFE_SOURCE_METADATA_KEYS}


class RejectedAuthCallbackLog:
    """Append-only audit log for callbacks that failed signature verification.

    Implements both the JSONL artifact surface and the SQLite mirror per
    ``contracts/rejected-auth-audit-log.md``.
    """

    def __init__(self, *, artifacts_root: Path, db_path: Path) -> None:
        self._artifacts_root = Path(artifacts_root)
        self._db_path = Path(db_path)

    def record(
        self,
        *,
        received_at: datetime,
        session_id: str | None,
        source_metadata: dict[str, str],
        http_status: int = 401,
    ) -> None:
        """Append one rejection row to both the JSONL artifact and the SQLite mirror.

        ``session_id`` MAY be ``None`` (forged callback not associatable with any
        session) → the row lands under ``artifacts/_unassociated/``. ``http_status``
        MUST be 401 (the SQLite CHECK enforces it). ``source_metadata`` is
        allowlist-scrubbed; the secret and body are never accepted.
        """
        safe_metadata = _scrub_source_metadata(source_metadata)
        received_at_iso = received_at.isoformat()

        row = {
            "received_at": received_at_iso,
            "session_id": session_id,
            "source_metadata": safe_metadata,
            "http_status": http_status,
        }

        # JSONL surface.
        subdir = session_id if session_id is not None else _UNASSOCIATED_DIR
        jsonl_dir = self._artifacts_root / subdir
        jsonl_dir.mkdir(parents=True, exist_ok=True)
        with (jsonl_dir / _JSONL_NAME).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")

        # SQLite mirror.
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(_TABLE_DDL)
            conn.execute(
                "INSERT INTO rejected_auth_callbacks "
                "(received_at, session_id, source_metadata_json, http_status) "
                "VALUES (?, ?, ?, ?)",
                (received_at_iso, session_id, json.dumps(safe_metadata), http_status),
            )
            conn.commit()

    def count_for_session(self, session_id: str) -> int:
        """Return the count of rejected-auth callbacks for the named session (FR-036)."""
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(_TABLE_DDL)
            (count,) = conn.execute(
                "SELECT COUNT(*) FROM rejected_auth_callbacks WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return int(count)
