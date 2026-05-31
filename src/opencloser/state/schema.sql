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
    ended_at                TEXT,
    -- Slice 3 additions (data-model.md §2.1, §3). All nullable for backwards
    -- compatibility with Slice 1 / Slice 2 reads. The `mock_provider_call_id`
    -- column above remains the SignalWire-assigned call SID under the Slice 3
    -- rename `provider_call_id` (data-model.md §1.1) — no schema-level rename
    -- so that pre-Slice-3 session reads remain interpretable.
    runtime_identity_json       TEXT,
    operator_identity_current   TEXT,
    operator_identity_original  TEXT,
    run_mode                    TEXT CHECK (run_mode IN ('rehearsal', 'real_call')),
    grace_window_sec            INTEGER,
    shadow_stt_enabled          INTEGER CHECK (shadow_stt_enabled IN (0, 1)),
    finalized_at                TEXT,
    cm_writeback_started_at     TEXT
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

-- Slice 3 — Real Call, Real CRM (data-model.md §1.4, §1.7, §1.8, §3).
-- Three new audit-grade tables added by Slice 3. All are session-scoped where
-- a session exists; `rejected_auth_callbacks.session_id` is nullable because a
-- forged callback may not be associatable with any known session.

CREATE TABLE IF NOT EXISTS rejected_auth_callbacks (
    -- Distinct audit log for SignalWire callbacks that fail HMAC-SHA256
    -- signature verification (FR-008 + Round 2 Q9). MUST NOT contain the
    -- verification secret. MUST NOT contain the callback body content
    -- (defense in depth against reflected-payload leakage). The run report
    -- surfaces `rejected_auth_callbacks_count` per session.
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    received_at          TEXT NOT NULL,
    session_id           TEXT,
    source_metadata_json TEXT NOT NULL,
    http_status          INTEGER NOT NULL CHECK (http_status = 401)
);

CREATE INDEX IF NOT EXISTS idx_rejected_auth_session
    ON rejected_auth_callbacks(session_id);

CREATE TABLE IF NOT EXISTS shadow_stt_discrepancies (
    -- Shadow STT discrepancy records per FR-030 + FR-031. 9 atomic enum
    -- values reflect data-model.md §1.7 storage normalization (7 spec
    -- categories split into 9 atoms for storage clarity).
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id          TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    field               TEXT NOT NULL CHECK (field IN (
                            'opt_out', 'wrong_number', 'captured_email',
                            'callback_intent', 'preferred_callback_window',
                            'person_reached_name', 'person_reached_role',
                            'interest_level', 'final_disposition'
                        )),
    live_value          TEXT,
    shadow_value        TEXT,
    classification      TEXT NOT NULL CHECK (classification IN ('benign', 'uncertain')),
    review_task_reason  TEXT,
    recorded_at         TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_shadow_disc_session
    ON shadow_stt_discrepancies(session_id);

CREATE TABLE IF NOT EXISTS shadow_lane_truncated_events (
    -- At most one row per session: the shadow lane was still producing output
    -- AFTER the orchestrator's post-finalization grace window elapsed
    -- (FR-029 + Round 2 Q7). Audit-only by construction — MUST NOT mutate the
    -- finalized disposition and MUST NOT emit a new CRM write-back payload.
    session_id                 TEXT PRIMARY KEY NOT NULL
                               REFERENCES sessions(session_id) ON DELETE CASCADE,
    finalized_at               TEXT NOT NULL,
    grace_window_ended_at      TEXT NOT NULL,
    late_output_summary_json   TEXT NOT NULL,
    would_have_classified_as   TEXT CHECK (would_have_classified_as IN ('benign', 'uncertain'))
);

CREATE TABLE IF NOT EXISTS schema_meta (
    applied_at  TEXT PRIMARY KEY NOT NULL,
    version     TEXT NOT NULL
);
