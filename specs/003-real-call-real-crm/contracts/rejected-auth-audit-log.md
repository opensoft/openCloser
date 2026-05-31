# Contract: Rejected-by-Authentication Audit Log

**Slice 3** · **FR-008** (+ Round 2 Q9) · **FR-035** · **FR-036** · [plan.md](../plan.md) · [research.md §2, §10](../research.md)

The rejected-by-authentication audit log is a distinct audit artifact for SignalWire
callbacks that fail HMAC-SHA256 signature verification. It is separate from the
`CallbacksAuditLog` (which records duplicates and out-of-order deliveries) so that
attempted-forgery signals are clearly distinguishable from benign delivery anomalies.

## Python contract

```python
from typing import Protocol
from datetime import datetime
from opencloser.models import SessionId

class RejectedAuthCallbackLog(Protocol):
    """Distinct audit log for callbacks that fail signature verification."""

    def record(
        self,
        *,
        received_at: datetime,
        session_id: SessionId | None,             # nullable; may not be associatable
        source_metadata: dict[str, str],          # provider-supplied source ids / IP-level metadata
        http_status: int = 401,
    ) -> None:
        """Append a row. MUST NOT accept or store the verification secret.
        MUST NOT accept or store the callback body content."""

    def count_for_session(self, session_id: SessionId) -> int:
        """Return the count of rejected-auth callbacks for a session (for the
        run report per FR-036)."""
```

## Required behaviors

1. **Distinct from the callbacks audit log** (Round 2 Q9 Option B): rejected-auth callbacks
   MUST be stored in a separate artifact and a separate SQLite table — NOT mixed with the
   `CallbacksAuditLog` for duplicates / out-of-order events.

2. **Schema strictly bounded**: the stored row contains:
   - `received_at` (ISO8601)
   - `session_id` (nullable; some forged callbacks may not match any known session)
   - `source_metadata` (a JSON object with provider-supplied source identifiers /
     IP-level metadata where available)
   - `http_status` (always 401)

3. **No secret leakage** (FR-035, Round 2 Q9): the log MUST NOT contain:
   - The HMAC-SHA256 verification secret.
   - The failed signature value.
   - The full callback body content.
   - Any other credential string.

4. **Defense in depth — no body content**: even if the body would not contain a secret,
   storing it risks reflected-payload leakage. The body is explicitly excluded.

5. **Run-report integration** (FR-036): the run report MUST surface
   `rejected_auth_callbacks_count` per session so operators see attempted forgeries.

6. **HTTP response**: the SignalWire callback receiver MUST respond with HTTP 401 (or the
   provider-appropriate failure code) when signature verification fails.

7. **On-disk file**: `artifacts/<session_id>/rejected_auth_callbacks.jsonl` (one JSON
   object per line). When `session_id` is null (unassociatable callback), the file may
   live at `artifacts/_unassociated/rejected_auth_callbacks.jsonl`.

## File format

```jsonl
{"received_at":"2026-05-25T14:00:00Z","session_id":"sess_abc123","source_metadata":{"sw_source":"...","remote_addr":"203.0.113.5"},"http_status":401}
{"received_at":"2026-05-25T14:01:30Z","session_id":null,"source_metadata":{"remote_addr":"198.51.100.7"},"http_status":401}
```

## SQLite mirror

```sql
CREATE TABLE rejected_auth_callbacks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  received_at TEXT NOT NULL,
  session_id TEXT,                       -- nullable
  source_metadata_json TEXT NOT NULL,    -- JSON; NO secret, NO body
  http_status INTEGER NOT NULL,
  CHECK (http_status = 401)
);
CREATE INDEX idx_rejected_auth_session ON rejected_auth_callbacks(session_id);
```

The SQLite mirror exists so `count_for_session` is O(1) for the run report; the JSONL file
is the source of truth for human inspection.

## Contract test summary (`tests/contract/test_rejected_auth_audit_log.py`)

| Test | Assertion |
|---|---|
| `test_record_appends_row` | `record(...)` appends to both the SQLite table and the JSONL file |
| `test_distinct_from_callbacks_audit_log` | Rows appear in `rejected_auth_callbacks.jsonl`, NOT in `callbacks_audit.jsonl` |
| `test_schema_excludes_secret_and_body` | Inspecting any stored row contains 0 substrings matching `SIGNALWIRE_SIGNING_SECRET` or any known body-content fixture |
| `test_unassociated_callback_session_id_null` | A forged callback that cannot be matched to a session has `session_id=null` and lands in `artifacts/_unassociated/...` |
| `test_http_status_is_401` | All recorded rows have `http_status = 401`; the CHECK constraint enforces it |
| `test_count_for_session_matches_jsonl` | `count_for_session(sid)` matches the line count of `artifacts/<sid>/rejected_auth_callbacks.jsonl` |
| `test_run_report_surfaces_count` | After N rejected-auth callbacks for a session, `run_report.json` shows `rejected_auth_callbacks_count = N` |
| `test_no_secrets_in_artifact_files` | grep for any `SIGNALWIRE_SIGNING_SECRET` substring across all `artifacts/**/rejected_auth_callbacks.jsonl` files returns 0 matches (SC-018) |
