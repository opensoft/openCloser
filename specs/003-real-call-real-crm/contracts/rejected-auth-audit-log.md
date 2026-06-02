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
     IP-level metadata where available) — restricted to an ALLOW-LIST of non-caller-controlled
     fields (provider source identifier(s) + remote IP / transport metadata only) and bounded
     at ≤ 1 KB serialized / ≤ 16 keys (Round 3), so a forged callback cannot stuff arbitrary
     payload into the audit log
   - `http_status` (always 401)

3. **No secret leakage** (FR-035, Round 2 Q9): the log MUST NOT contain:
   - The HMAC-SHA256 verification secret.
   - The failed signature value.
   - The full callback body content.
   - Any other credential string.

4. **Defense in depth — no body content**: even if the body would not contain a secret,
   storing it risks reflected-payload leakage. The body is explicitly excluded. On a
   verification failure the ASGI receiver MUST drop the request body buffer without persisting
   it anywhere (Round 3).

4b. **Append one row per delivery — no dedup** (Round 4 R4-Q27): the rejected-auth audit log
    appends exactly one row per forged delivery; every forged delivery is recorded and there is
    NO deduplication. Each attempt is independently security-relevant, so even repeated forged
    deliveries (including null-`session_id` duplicates) are each recorded as their own row.

4a. **Unassociated-rejection retention** (Round 3): a null-`session_id` rejection is written
    under `artifacts/_unassociated/rejected_auth_callbacks.jsonl`, which MUST honor the same
    ≥ 90-day local-artifact retention floor as session-scoped artifacts. Its count is surfaced
    as a deployment-level `rejected_auth_unassociated_count` in operator tooling (the per-session
    run report's `rejected_auth_callbacks_count` covers only session-scoped rejections).

5. **Run-report integration** (FR-036): the run report MUST surface
   `rejected_auth_callbacks_count` per session so operators see attempted forgeries.

6. **HTTP response**: the SignalWire callback receiver MUST respond with HTTP 401 (or the
   provider-appropriate failure code) when signature verification fails.

7. **On-disk file**: `artifacts/<session_id>/rejected_auth_callbacks.jsonl` (one JSON
   object per line). When `session_id` is null (unassociatable callback), the file may
   live at `artifacts/_unassociated/rejected_auth_callbacks.jsonl`.

8. **Unassociatable rule** (Round 4 R4-Q19): a callback is "unassociatable" when its
   `{session_id}` URL path segment matches no known session row (or the segment is absent).
   An unassociatable callback resolves to a null `session_id` and its rejection row is written
   under `artifacts/_unassociated/rejected_auth_callbacks.jsonl`. This is the sole definition
   of how a rejection becomes null-session.

9. **Path-traversal sanitization before composing the write path** (CHK169): the
   attacker-controlled `{session_id}` URL path segment MUST be validated/sanitized BEFORE it is
   used as a filesystem path component. The receiver MUST treat `{session_id}` as untrusted
   input on the forged-callback path (signature verification has already failed, so the segment
   is not authenticated). A segment is admissible as a path component ONLY if it matches the
   canonical session-id format (an allow-list charset, e.g. `^sess_[A-Za-z0-9]+$`); any segment
   containing path-traversal or separator characters (`..`, `/`, `\`, NUL, absolute-path
   prefixes) or otherwise failing the allow-list MUST NOT be used to compose
   `artifacts/<session_id>/rejected_auth_callbacks.jsonl`. Such a segment is treated as
   unassociatable (per #8) and its row is written under
   `artifacts/_unassociated/rejected_auth_callbacks.jsonl`. The composed write path MUST further
   be confined to the artifacts root (resolved/realpath MUST remain inside the artifacts
   directory) so a forged `{session_id}` (e.g. `../../etc`) can NEVER steer the rejected-auth
   log write outside the artifacts root. Note that the #8 known-session match already rejects
   most forged ids, but sanitization is a SEPARATE, independent fail-closed gate applied before
   any path composition (defense in depth: it holds even if a future change relaxes the
   known-session match).

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
| `test_source_metadata_allow_list_and_size_bound` | A callback carrying extra / oversized metadata is stored with only allow-listed keys, ≤ 16 keys, ≤ 1 KB serialized (Round 3) |
| `test_body_buffer_dropped_on_failure` | After a verification failure, the request body is not present in any persisted store or in memory beyond the request scope (Round 3) |
| `test_unassociated_retention_floor` | `artifacts/_unassociated/rejected_auth_callbacks.jsonl` is subject to the same ≥ 90-day retention floor; operator tooling reports `rejected_auth_unassociated_count` (Round 3) |
| `test_append_one_row_per_delivery_no_dedup` | N forged deliveries (including repeated null-`session_id` deliveries) append N rows; no dedup collapses repeated attempts (Round 4 R4-Q27) |
| `test_unassociatable_rule_defined` | A callback whose `{session_id}` path segment matches no known session row (or is absent) resolves to null `session_id` and lands under `artifacts/_unassociated/` (Round 4 R4-Q19) |
| `test_session_id_path_traversal_sanitized` | A forged `{session_id}` containing traversal/separator characters (e.g. `../../etc`, `a/b`, NUL) fails the allow-list, is NOT used to compose the write path, lands under `artifacts/_unassociated/`, and the resolved write path stays confined inside the artifacts root — no write occurs outside it (CHK169) |

## Round 4 — Checklist-Residual Alignment (2026-06-01)

Propagated from spec §"Session 2026-06-01 (Round 4 — checklist residual closure)":
- R4-Q27: the rejected-auth audit log appends one row per delivery with NO dedup; every forged
  delivery — including null-`session_id` duplicates — is each recorded. Stated in Required
  behaviors; added `test_append_one_row_per_delivery_no_dedup`.
- R4-Q19: defined the unassociatable rule — a callback whose `{session_id}` path segment
  matches no known session row (or is absent) → null `session_id` → `artifacts/_unassociated/`.
  Added `test_unassociatable_rule_defined`.
