# Data Model: Slice 1 — Mock Call, Mock CRM

**Plan**: [plan.md](./plan.md)
**Spec**: [spec.md](./spec.md) (Key Entities + FR-002, FR-004, FR-007, FR-014, FR-019, FR-020, FR-021, FR-028–FR-036)
**Created**: 2026-05-19

This document specifies the SQLite schema and Pydantic entity shapes that satisfy every Key Entity and FR in the spec.

---

## Storage model

Slice 1 uses a single SQLite database at `./state/slice1.db` (configurable via `OPENCLOSER_STATE_DB`). The schema lives in `src/opencloser/state/schema.sql` and is applied on startup if absent (CREATE TABLE IF NOT EXISTS). PRAGMAs set on every connection:

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA synchronous = NORMAL;
```

All `TEXT` timestamp columns hold ISO 8601 / UTC / millisecond strings (`YYYY-MM-DDTHH:MM:SS.sssZ`) per FR-014.

---

## ER diagram (textual)

```text
queue_items 1──n eligibility_decisions 1──1 sessions
                                              │
                                              ├──n mock_call_events
                                              ├──n idempotency_keys
                                              ├──n conflicting_event_audit_records
                                              ├──0..1 normalized_results  (projection)
                                              ├──0..1 phone_call_activities
                                              ├──1    queue_status_updates
                                              └──0..1 task_payloads
```

Every processed queue-item ID produces exactly one `sessions` row (FR-005). Eligibility-allowed sessions also produce up to one of each write-back payload row; eligibility-blocked sessions produce only the `queue_status_updates` row (FR-031 mapping).

---

## Schema (DDL)

```sql
-- src/opencloser/state/schema.sql

-- =======================================================================
-- Queue Item (FR-002, Key Entities)
-- =======================================================================
CREATE TABLE IF NOT EXISTS queue_items (
  queue_item_id        TEXT PRIMARY KEY NOT NULL,
  facility_name        TEXT NOT NULL,
  phone_number         TEXT,                            -- nullable; FR-004(a) blocks if NULL
  timezone             TEXT,                            -- IANA tz name; nullable triggers default-tz fallback
  default_tz_applied   INTEGER NOT NULL DEFAULT 0,      -- 0/1; set when fallback applied
  email                TEXT,                            -- optional pre-populated email
  attempt_count        INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
  dnc_flag             INTEGER NOT NULL DEFAULT 0,      -- 0/1
  callable_status      TEXT NOT NULL
                       CHECK (callable_status IN ('ready','in_progress','completed','blocked','dnc')),
  last_decision_at     TEXT                             -- ISO 8601 UTC ms; nullable until first decision
);

-- =======================================================================
-- Eligibility Decision (FR-004, FR-005, Key Entities)
-- =======================================================================
CREATE TABLE IF NOT EXISTS eligibility_decisions (
  decision_id          TEXT PRIMARY KEY NOT NULL,
  queue_item_id        TEXT NOT NULL REFERENCES queue_items(queue_item_id) ON DELETE CASCADE,
  decided_at           TEXT NOT NULL,                   -- ISO 8601 UTC ms
  outcome              TEXT NOT NULL CHECK (outcome IN ('allow','block')),
  rule_a_phone_pass            INTEGER NOT NULL,        -- 0/1 per rule
  rule_b_timezone_pass         INTEGER NOT NULL,
  rule_c_call_window_pass      INTEGER NOT NULL,
  rule_d_dnc_pass              INTEGER NOT NULL,
  rule_e_max_attempts_pass     INTEGER NOT NULL,
  rule_f_callable_status_pass  INTEGER NOT NULL,
  failing_rules        TEXT,                            -- JSON array of FR-004 rule letters; populated only when outcome='block'
  default_tz_substituted_for   TEXT,                    -- original record-timezone value when default was substituted
  session_id           TEXT NOT NULL                    -- FR-005 always-create-session
                       REFERENCES sessions(session_id) DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX IF NOT EXISTS idx_eligibility_decisions_queue_item
  ON eligibility_decisions(queue_item_id);

-- =======================================================================
-- Session (FR-005, FR-012, FR-013, Key Entities)
-- =======================================================================
CREATE TABLE IF NOT EXISTS sessions (
  session_id           TEXT PRIMARY KEY NOT NULL,
  queue_item_id        TEXT NOT NULL REFERENCES queue_items(queue_item_id) ON DELETE CASCADE,
  persona_version      TEXT,                            -- set only when persona ran
  state                TEXT NOT NULL DEFAULT 'created'
                       CHECK (state IN ('created','eligibility_evaluated','in_flight','finalized','blocked')),
  final_disposition    TEXT
                       CHECK (final_disposition IN (
                         'interested_callback_requested','interested_email_captured',
                         'not_interested','call_back_later','wrong_number',
                         'no_answer','voicemail','do_not_call',
                         'needs_human_review','failed','blocked'
                       )),
  blocked_reason       TEXT,                            -- JSON array of failing rule letters; only for disposition='blocked'
  mock_provider_call_id TEXT UNIQUE,                    -- FR-007 globally unique; NULL for blocked sessions
  started_at           TEXT NOT NULL,                   -- ISO 8601 UTC ms
  ended_at             TEXT                             -- NULL until finalized
);

CREATE INDEX IF NOT EXISTS idx_sessions_queue_item ON sessions(queue_item_id);

-- =======================================================================
-- Mock Call Event (FR-006, FR-019, Key Entities)
-- =======================================================================
CREATE TABLE IF NOT EXISTS mock_call_events (
  -- composite PK: a given (session, event_id) is the FR-019 idempotency anchor for raw events
  session_id           TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  event_id             TEXT NOT NULL,
  event_type           TEXT NOT NULL
                       CHECK (event_type IN ('connected','no_answer','voicemail','failed','completed','callback_requested')),
  received_at          TEXT NOT NULL,                   -- ISO 8601 UTC ms
  payload_json         TEXT NOT NULL DEFAULT '{}',      -- raw event payload as JSON text
  PRIMARY KEY (session_id, event_id)
);

CREATE INDEX IF NOT EXISTS idx_mock_call_events_session ON mock_call_events(session_id);

-- =======================================================================
-- Idempotency Key (FR-019, Key Entities)
-- =======================================================================
CREATE TABLE IF NOT EXISTS idempotency_keys (
  -- composite PK is the FR-019 key itself
  session_id           TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  mock_provider_call_id TEXT,                           -- nullable for non-call-scoped writes (e.g., blocked queue-status)
  event_id             TEXT,                            -- nullable when not tied to a specific event
  write_back_kind      TEXT NOT NULL
                       CHECK (write_back_kind IN (
                         'session_state','normalized_result','attempt_count',
                         'phone_call_activity','queue_status_update','task_payload','exported_artifact'
                       )),
  applied_at           TEXT NOT NULL,                   -- ISO 8601 UTC ms
  PRIMARY KEY (session_id, COALESCE(mock_provider_call_id,''), COALESCE(event_id,''), write_back_kind)
);

-- =======================================================================
-- Conflicting Event Audit Record (FR-020, Key Entities)
-- =======================================================================
CREATE TABLE IF NOT EXISTS conflicting_event_audit_records (
  audit_id             TEXT PRIMARY KEY NOT NULL,
  session_id           TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  event_id             TEXT NOT NULL,
  conflicting_event_type TEXT NOT NULL,
  received_at          TEXT NOT NULL,
  full_event_payload_json TEXT NOT NULL,
  preserved_disposition TEXT NOT NULL                  -- the finalized disposition that was preserved
);

CREATE INDEX IF NOT EXISTS idx_conflicting_events_session
  ON conflicting_event_audit_records(session_id);

-- =======================================================================
-- Phone Call Activity (FR-028)
-- =======================================================================
CREATE TABLE IF NOT EXISTS phone_call_activities (
  session_id           TEXT PRIMARY KEY NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  queue_item_id        TEXT NOT NULL REFERENCES queue_items(queue_item_id) ON DELETE CASCADE,
  mock_provider_call_id TEXT NOT NULL,
  persona_version      TEXT NOT NULL,
  final_disposition    TEXT NOT NULL,
  summary              TEXT NOT NULL,
  started_at           TEXT NOT NULL,
  ended_at             TEXT NOT NULL
);

-- =======================================================================
-- Queue Status Update (FR-029)
-- =======================================================================
CREATE TABLE IF NOT EXISTS queue_status_updates (
  session_id           TEXT PRIMARY KEY NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  queue_item_id        TEXT NOT NULL REFERENCES queue_items(queue_item_id) ON DELETE CASCADE,
  previous_status      TEXT NOT NULL,
  new_status           TEXT NOT NULL
                       CHECK (new_status IN ('ready','in_progress','completed','blocked','dnc')),
  transition_reason    TEXT NOT NULL,
  transition_at        TEXT NOT NULL
);

-- =======================================================================
-- Task Payload (FR-030)
-- =======================================================================
CREATE TABLE IF NOT EXISTS task_payloads (
  task_id              TEXT PRIMARY KEY NOT NULL,
  session_id           TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  queue_item_id        TEXT NOT NULL REFERENCES queue_items(queue_item_id) ON DELETE CASCADE,
  task_kind            TEXT NOT NULL CHECK (task_kind IN ('callback','review')),
  subject              TEXT NOT NULL,
  reason_code          TEXT,                            -- non-null for task_kind='review' (FR-035)
  preferred_callback_window TEXT,                       -- non-null for task_kind='callback' when window was captured
  captured_email       TEXT,                            -- non-null when verified email accompanies callback (Q5 Clarification)
  persona_version      TEXT NOT NULL,
  created_at           TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_task_payloads_session ON task_payloads(session_id);

-- =======================================================================
-- Normalized Result (FR-012, FR-014) — stored as a flat row for fast read
-- =======================================================================
CREATE TABLE IF NOT EXISTS normalized_results (
  session_id           TEXT PRIMARY KEY NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  queue_item_id        TEXT NOT NULL REFERENCES queue_items(queue_item_id) ON DELETE CASCADE,
  mock_provider_call_id TEXT,
  persona_version      TEXT,
  final_disposition    TEXT NOT NULL,
  summary              TEXT,
  transcript_pointer   TEXT,                            -- relative path; NULL for summary-only retention
  captured_email       TEXT,                            -- verified
  captured_email_unverified TEXT,                       -- mutually exclusive with captured_email
  callback_requested   INTEGER NOT NULL DEFAULT 0,
  preferred_callback_window TEXT,
  human_review_reason  TEXT,                            -- from FR-035 enum when disposition='needs_human_review'
  blocked_reason       TEXT,                            -- JSON array; only when disposition='blocked'
  started_at           TEXT NOT NULL,
  ended_at             TEXT NOT NULL,
  CHECK (captured_email IS NULL OR captured_email_unverified IS NULL)  -- mutually exclusive
);
```

---

## Pydantic models (`src/opencloser/models.py`)

The Pydantic v2 models mirror the schema 1:1, with field validators that enforce the SQLite CHECK constraints at the Python layer. Key shapes:

```python
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from pydantic import BaseModel, Field, model_validator

# ---- enums ----

class CallableStatus(StrEnum):
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    DNC = "dnc"

class Disposition(StrEnum):
    INTERESTED_CALLBACK_REQUESTED = "interested_callback_requested"
    INTERESTED_EMAIL_CAPTURED = "interested_email_captured"
    NOT_INTERESTED = "not_interested"
    CALL_BACK_LATER = "call_back_later"
    WRONG_NUMBER = "wrong_number"
    NO_ANSWER = "no_answer"
    VOICEMAIL = "voicemail"
    DO_NOT_CALL = "do_not_call"
    NEEDS_HUMAN_REVIEW = "needs_human_review"
    FAILED = "failed"
    BLOCKED = "blocked"

class HumanReviewReason(StrEnum):
    UNCERTAIN_ROLE = "uncertain_role"
    UNCERTAIN_INTENT = "uncertain_intent"
    AMBIGUOUS_DNC = "ambiguous_dnc"
    CAPTURED_EMAIL_INVALID_NO_CALLBACK = "captured_email_invalid_no_callback"
    PHI_COLLECTION_RISK = "phi_collection_risk"
    LEGAL_REQUEST = "legal_request"
    NON_CLINICAL_TOPIC_ESCALATION = "non_clinical_topic_escalation"
    OUTSIDE_ALLOWED_CLAIMS = "outside_allowed_claims"
    SCRIPT_TRUNCATED = "script_truncated"

# ---- shared types ----

# An ISO 8601 UTC ms timestamp string. Validators ensure shape.
UtcMs = Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")]

# ---- core entities (one Pydantic class per table) ----

class QueueItem(BaseModel):
    queue_item_id: str
    facility_name: str
    phone_number: str | None = None
    timezone: str | None = None
    default_tz_applied: bool = False
    email: str | None = None
    attempt_count: int = Field(ge=0)
    dnc_flag: bool = False
    callable_status: CallableStatus
    last_decision_at: UtcMs | None = None

class EligibilityDecision(BaseModel):
    decision_id: str
    queue_item_id: str
    decided_at: UtcMs
    outcome: Literal["allow", "block"]
    rule_a_phone_pass: bool
    rule_b_timezone_pass: bool
    rule_c_call_window_pass: bool
    rule_d_dnc_pass: bool
    rule_e_max_attempts_pass: bool
    rule_f_callable_status_pass: bool
    failing_rules: list[Literal["a","b","c","d","e","f"]] = []
    default_tz_substituted_for: str | None = None
    session_id: str

class Session(BaseModel):
    session_id: str
    queue_item_id: str
    persona_version: str | None = None
    state: Literal["created","eligibility_evaluated","in_flight","finalized","blocked"]
    final_disposition: Disposition | None = None
    blocked_reason: list[Literal["a","b","c","d","e","f"]] | None = None
    mock_provider_call_id: str | None = None
    started_at: UtcMs
    ended_at: UtcMs | None = None

class NormalizedResult(BaseModel):
    """Exported as session-result.json. FR-014 fields."""
    schema_version: Literal["slice1-v1"] = "slice1-v1"
    session_id: str
    queue_item_id: str
    mock_provider_call_id: str | None = None
    persona_version: str | None = None
    final_disposition: Disposition
    summary: str | None = None
    transcript_pointer: str | None = None
    captured_email: str | None = None
    captured_email_unverified: str | None = None
    callback_requested: bool = False
    preferred_callback_window: str | None = None
    human_review_reason: HumanReviewReason | None = None
    blocked_reason: list[Literal["a","b","c","d","e","f"]] | None = None
    started_at: UtcMs
    ended_at: UtcMs

    @model_validator(mode="after")
    def _exclusive_email_fields(self):
        if self.captured_email and self.captured_email_unverified:
            raise ValueError("captured_email and captured_email_unverified are mutually exclusive")
        return self

class PhoneCallActivityPayload(BaseModel):
    """FR-028. Emitted via writeback.json under `phone_call_activity` key."""
    schema_version: Literal["slice1-v1"] = "slice1-v1"
    session_id: str
    queue_item_id: str
    mock_provider_call_id: str
    persona_version: str
    final_disposition: Disposition
    summary: str
    started_at: UtcMs
    ended_at: UtcMs

class QueueStatusUpdatePayload(BaseModel):
    """FR-029. Always emitted exactly once per session."""
    schema_version: Literal["slice1-v1"] = "slice1-v1"
    session_id: str
    queue_item_id: str
    previous_status: CallableStatus
    new_status: CallableStatus
    transition_reason: str
    transition_at: UtcMs

class TaskPayload(BaseModel):
    """FR-030. Emitted only when FR-031 mapping says so."""
    schema_version: Literal["slice1-v1"] = "slice1-v1"
    task_id: str
    session_id: str
    queue_item_id: str
    task_kind: Literal["callback","review"]
    subject: str
    reason_code: HumanReviewReason | None = None     # required for review tasks
    preferred_callback_window: str | None = None     # required for callback tasks when window captured
    captured_email: str | None = None                # populated when verified email accompanies callback
    persona_version: str
    created_at: UtcMs

    @model_validator(mode="after")
    def _kind_invariants(self):
        if self.task_kind == "review" and self.reason_code is None:
            raise ValueError("review task requires reason_code")
        return self

class WriteBack(BaseModel):
    """The composite writeback.json artifact."""
    schema_version: Literal["slice1-v1"] = "slice1-v1"
    session_id: str
    phone_call_activity: PhoneCallActivityPayload | None = None
    queue_status_update: QueueStatusUpdatePayload
    task: TaskPayload | None = None

class ConflictingEventAuditRecord(BaseModel):
    """FR-020."""
    audit_id: str
    session_id: str
    event_id: str
    conflicting_event_type: str
    received_at: UtcMs
    full_event_payload: dict
    preserved_disposition: Disposition

class ExportedEligibilityDecision(BaseModel):
    """eligibility-decision.json artifact."""
    schema_version: Literal["slice1-v1"] = "slice1-v1"
    decision_id: str
    queue_item_id: str
    session_id: str
    decided_at: UtcMs
    outcome: Literal["allow", "block"]
    rules: dict[Literal["a","b","c","d","e","f"], bool]
    failing_rules: list[Literal["a","b","c","d","e","f"]]
    default_tz_substituted_for: str | None = None
```

---

## Lifecycle invariants

1. **One-session-per-queue-run** (FR-005): every CLI invocation that processes a `queue_item_id` MUST INSERT exactly one row into `sessions`. Blocked-by-eligibility runs INSERT a session with `state='blocked'`, `final_disposition='blocked'`, and `mock_provider_call_id IS NULL`.
2. **Eligibility decision precedes session finalization for allowed sessions**: `eligibility_decisions.outcome='allow'` ⇒ `sessions.state` transitions through `eligibility_evaluated → in_flight → finalized`.
3. **Attempt-count anchor** (FR-021): exactly one INCREMENT of `queue_items.attempt_count` per `mock_provider_call_id`, applied at INSERT of the first `mock_call_events` row for that `mock_provider_call_id`. Subsequent INSERTs against the same `mock_provider_call_id` MUST NOT re-increment.
4. **Idempotency check ordering**: every state-mutating operation in the orchestrator (write to `sessions`, `mock_call_events`, `phone_call_activities`, `queue_status_updates`, `task_payloads`, or attempt-count update) MUST first attempt INSERT into `idempotency_keys` and treat a UNIQUE-constraint violation as "duplicate, no-op". This makes FR-019 a single-line invariant.
5. **No mutation after finalization** (FR-020): once `sessions.state='finalized'`, no UPDATE may change `final_disposition`. Conflicting late events go to `conflicting_event_audit_records` only.
6. **Mutually exclusive email fields**: `normalized_results.captured_email` and `normalized_results.captured_email_unverified` enforced by CHECK constraint + Pydantic model_validator.

---

## Migration & versioning

Slice 1 has no migrations — the schema is the initial state. A `schema_meta` table records the active version:

```sql
CREATE TABLE IF NOT EXISTS schema_meta (
  applied_at  TEXT PRIMARY KEY NOT NULL,
  version     TEXT NOT NULL
);
-- Seed: INSERT INTO schema_meta VALUES (<now_utc_ms>, 'slice1-v1');
```

Slice 2 will introduce a migration table proper.

---

## Test fixtures touchpoints

- `tests/conftest.py` creates a temporary SQLite DB per test, applies `schema.sql`, and yields a fresh DAO. This is the SC-009 isolation-stub for everything other than the module under test.
- `tests/fixtures/queue_items/*.json` are loaded into `queue_items` via the same DAO at test setup.
- `tests/fixtures/conversations/*.json` and `tests/fixtures/transport_events/*.json` are NOT loaded into the DB; they are read by the persona and mock-transport modules respectively.
