-- openCloser Slice 1 — SQLite schema (data-model.md §Schema).
--
-- PRAGMAs applied by state/store.py at every connection:
--   PRAGMA journal_mode = WAL;
--   PRAGMA foreign_keys = ON;
--   PRAGMA synchronous = NORMAL;
--
-- Timestamps are TEXT in ISO 8601 / UTC / millisecond format (e.g., 2026-05-19T17:00:00.000Z) per FR-014.

CREATE TABLE IF NOT EXISTS queue_items (
    queue_item_id       TEXT PRIMARY KEY NOT NULL,
    facility_name       TEXT NOT NULL,
    phone_number        TEXT,
    timezone            TEXT,
    default_tz_applied  INTEGER NOT NULL DEFAULT 0 CHECK (default_tz_applied IN (0, 1)),
    email               TEXT,
    attempt_count       INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    dnc_flag            INTEGER NOT NULL DEFAULT 0 CHECK (dnc_flag IN (0, 1)),
    callable_status     TEXT NOT NULL
                        CHECK (callable_status IN ('ready', 'in_progress', 'completed', 'blocked', 'dnc')),
    last_decision_at    TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id              TEXT PRIMARY KEY NOT NULL,
    queue_item_id           TEXT NOT NULL REFERENCES queue_items(queue_item_id) ON DELETE CASCADE,
    persona_version         TEXT,
    state                   TEXT NOT NULL DEFAULT 'created'
                            CHECK (state IN ('created', 'eligibility_evaluated', 'in_flight', 'finalized', 'blocked')),
    final_disposition       TEXT
                            CHECK (final_disposition IN (
                                'interested_callback_requested', 'interested_email_captured',
                                'not_interested', 'call_back_later', 'wrong_number',
                                'no_answer', 'voicemail', 'do_not_call',
                                'needs_human_review', 'failed', 'blocked'
                            )),
    blocked_reason          TEXT,
    mock_provider_call_id   TEXT UNIQUE,
    started_at              TEXT NOT NULL,
    ended_at                TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_queue_item ON sessions(queue_item_id);

CREATE TABLE IF NOT EXISTS eligibility_decisions (
    decision_id                  TEXT PRIMARY KEY NOT NULL,
    queue_item_id                TEXT NOT NULL REFERENCES queue_items(queue_item_id) ON DELETE CASCADE,
    decided_at                   TEXT NOT NULL,
    outcome                      TEXT NOT NULL CHECK (outcome IN ('allow', 'block')),
    rule_a_phone_pass            INTEGER NOT NULL CHECK (rule_a_phone_pass IN (0, 1)),
    rule_b_timezone_pass         INTEGER NOT NULL CHECK (rule_b_timezone_pass IN (0, 1)),
    rule_c_call_window_pass      INTEGER NOT NULL CHECK (rule_c_call_window_pass IN (0, 1)),
    rule_d_dnc_pass              INTEGER NOT NULL CHECK (rule_d_dnc_pass IN (0, 1)),
    rule_e_max_attempts_pass     INTEGER NOT NULL CHECK (rule_e_max_attempts_pass IN (0, 1)),
    rule_f_callable_status_pass  INTEGER NOT NULL CHECK (rule_f_callable_status_pass IN (0, 1)),
    failing_rules                TEXT,
    default_tz_applied           INTEGER NOT NULL DEFAULT 0 CHECK (default_tz_applied IN (0, 1)),
    default_tz_substituted_for   TEXT,
    -- DEFERRABLE INITIALLY DEFERRED (data-model.md §Schema): the FK is checked at COMMIT,
    -- not at row INSERT, so the orchestrator may persist the decision and its session in
    -- either order within one transaction.
    session_id                   TEXT NOT NULL
                                 REFERENCES sessions(session_id) ON DELETE CASCADE
                                 DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX IF NOT EXISTS idx_eligibility_decisions_queue_item ON eligibility_decisions(queue_item_id);

CREATE TABLE IF NOT EXISTS mock_call_events (
    session_id      TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    event_id        TEXT NOT NULL,
    event_type      TEXT NOT NULL
                    CHECK (event_type IN ('connected', 'no_answer', 'voicemail', 'failed', 'completed', 'callback_requested')),
    received_at     TEXT NOT NULL,
    payload_json    TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (session_id, event_id)
);

CREATE INDEX IF NOT EXISTS idx_mock_call_events_session ON mock_call_events(session_id);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    session_id              TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    mock_provider_call_id   TEXT NOT NULL DEFAULT '',
    event_id                TEXT NOT NULL DEFAULT '',
    write_back_kind         TEXT NOT NULL
                            CHECK (write_back_kind IN (
                                'session_state', 'normalized_result', 'attempt_count',
                                'phone_call_activity', 'queue_status_update', 'task_payload', 'exported_artifact'
                            )),
    applied_at              TEXT NOT NULL,
    PRIMARY KEY (session_id, mock_provider_call_id, event_id, write_back_kind)
);

CREATE TABLE IF NOT EXISTS conflicting_event_audit_records (
    audit_id                 TEXT PRIMARY KEY NOT NULL,
    session_id               TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    event_id                 TEXT NOT NULL,
    conflicting_event_type   TEXT NOT NULL
                             CHECK (conflicting_event_type IN ('connected', 'no_answer', 'voicemail', 'failed', 'completed', 'callback_requested')),
    received_at              TEXT NOT NULL,
    full_event_payload_json  TEXT NOT NULL,
    preserved_disposition    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_conflicting_events_session ON conflicting_event_audit_records(session_id);

CREATE TABLE IF NOT EXISTS phone_call_activities (
    session_id              TEXT PRIMARY KEY NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    queue_item_id           TEXT NOT NULL REFERENCES queue_items(queue_item_id) ON DELETE CASCADE,
    mock_provider_call_id   TEXT NOT NULL,
    persona_version         TEXT NOT NULL,
    final_disposition       TEXT NOT NULL,
    summary                 TEXT NOT NULL,
    started_at              TEXT NOT NULL,
    ended_at                TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS queue_status_updates (
    session_id          TEXT PRIMARY KEY NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    queue_item_id       TEXT NOT NULL REFERENCES queue_items(queue_item_id) ON DELETE CASCADE,
    previous_status     TEXT NOT NULL,
    new_status          TEXT NOT NULL
                        CHECK (new_status IN ('ready', 'in_progress', 'completed', 'blocked', 'dnc')),
    transition_reason   TEXT NOT NULL,
    transition_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_payloads (
    task_id                     TEXT PRIMARY KEY NOT NULL,
    session_id                  TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    queue_item_id               TEXT NOT NULL REFERENCES queue_items(queue_item_id) ON DELETE CASCADE,
    task_kind                   TEXT NOT NULL CHECK (task_kind IN ('callback', 'review')),
    subject                     TEXT NOT NULL,
    reason_code                 TEXT,
    preferred_callback_window   TEXT,
    captured_email              TEXT,
    assigned_to                 TEXT,
    persona_version             TEXT NOT NULL,
    created_at                  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_task_payloads_session ON task_payloads(session_id);

CREATE TABLE IF NOT EXISTS normalized_results (
    session_id                  TEXT PRIMARY KEY NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    queue_item_id               TEXT NOT NULL REFERENCES queue_items(queue_item_id) ON DELETE CASCADE,
    mock_provider_call_id       TEXT,
    persona_version             TEXT,
    final_disposition           TEXT NOT NULL,
    summary                     TEXT,
    transcript_pointer          TEXT,
    captured_email              TEXT,
    captured_email_unverified   TEXT,
    callback_requested          INTEGER NOT NULL DEFAULT 0 CHECK (callback_requested IN (0, 1)),
    preferred_callback_window   TEXT,
    human_review_reason         TEXT,
    blocked_reason              TEXT,
    started_at                  TEXT NOT NULL,
    ended_at                    TEXT NOT NULL,
    CHECK (captured_email IS NULL OR captured_email_unverified IS NULL)
);

-- Slice 2 — CRM correlation + write-back progress (data-model.md §1).

CREATE TABLE IF NOT EXISTS crm_correlations (
    session_id           TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    record_kind          TEXT NOT NULL
                         CHECK (record_kind IN ('phone_call_activity', 'task', 'queue_status')),
    idempotency_key      TEXT NOT NULL,
    dataverse_record_id  TEXT,
    write_status         TEXT NOT NULL CHECK (write_status IN ('pending', 'confirmed', 'failed')),
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL,
    PRIMARY KEY (session_id, record_kind)
);

CREATE TABLE IF NOT EXISTS writeback_progress (
    session_id                 TEXT PRIMARY KEY NOT NULL
                               REFERENCES sessions(session_id) ON DELETE CASCADE,
    phone_call_activity_done   INTEGER NOT NULL DEFAULT 0
                               CHECK (phone_call_activity_done IN (0, 1)),
    queue_status_update_done   INTEGER NOT NULL DEFAULT 0
                               CHECK (queue_status_update_done IN (0, 1)),
    task_done                  INTEGER NOT NULL DEFAULT 0 CHECK (task_done IN (0, 1)),
    run_status                 TEXT NOT NULL
                               CHECK (run_status IN ('in_progress', 'completed', 'resume_needed', 'blocked')),
    last_error                 TEXT,
    updated_at                 TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schema_meta (
    applied_at  TEXT PRIMARY KEY NOT NULL,
    version     TEXT NOT NULL
);
