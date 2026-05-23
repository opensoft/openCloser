"""Pydantic v2 entity models per data-model.md §Pydantic models.

Mirrors the SQLite schema in src/opencloser/state/schema.sql 1:1 with field-level
validators that enforce the SQLite CHECK constraints at the Python layer.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# Enums (FR-002, FR-013, FR-035)
# ---------------------------------------------------------------------------


class CallableStatus(StrEnum):
    """FR-002 callable-status enum."""

    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    DNC = "dnc"


class Disposition(StrEnum):
    """FR-013 final-disposition enum (11 values; `blocked` added in Phase 1 clarifications)."""

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
    """FR-035 escalation reason codes (9 values, append-only per Slice 1 policy)."""

    UNCERTAIN_ROLE = "uncertain_role"
    UNCERTAIN_INTENT = "uncertain_intent"
    AMBIGUOUS_DNC = "ambiguous_dnc"
    CAPTURED_EMAIL_INVALID_NO_CALLBACK = "captured_email_invalid_no_callback"
    PHI_COLLECTION_RISK = "phi_collection_risk"
    LEGAL_REQUEST = "legal_request"
    NON_CLINICAL_TOPIC_ESCALATION = "non_clinical_topic_escalation"
    OUTSIDE_ALLOWED_CLAIMS = "outside_allowed_claims"
    SCRIPT_TRUNCATED = "script_truncated"


class RoleConfidence(StrEnum):
    """FR-034 extraction schema — role certainty only; engagement uncertainty is in IntentClassification."""

    CONFIDENT_DECISION_MAKER = "confident_decision_maker"
    CONFIDENT_NON_DECISION_MAKER = "confident_non_decision_maker"
    UNCERTAIN = "uncertain"


class IntentClassification(StrEnum):
    """FR-034 extraction schema — intent enum."""

    INTERESTED = "interested"
    NOT_INTERESTED = "not_interested"
    CALL_BACK_LATER = "call_back_later"
    DNC_STATED = "dnc_stated"
    WRONG_NUMBER = "wrong_number"
    UNCERTAIN = "uncertain"


class RefusalTopic(StrEnum):
    """FR-034 refusal_topics — enumerated set; free-form forbidden in Slice 1."""

    CLINICAL_ADVICE = "clinical_advice"
    LEGAL_ADVICE = "legal_advice"
    REGULATORY_INTERPRETATION = "regulatory_interpretation"
    INSURANCE_DISPUTE = "insurance_dispute"
    COMPETITOR_COMPARISON = "competitor_comparison"
    PRICING_SPECIFIC = "pricing_specific"
    MEDICAL_HISTORY = "medical_history"


class EventType(StrEnum):
    """FR-006 mock call event types."""

    CONNECTED = "connected"
    NO_ANSWER = "no_answer"
    VOICEMAIL = "voicemail"
    FAILED = "failed"
    COMPLETED = "completed"
    CALLBACK_REQUESTED = "callback_requested"


class FailureReason(StrEnum):
    """Per Clarifications Round 2 Q15 — `failed` event payload enum."""

    CARRIER_ERROR = "carrier_error"
    TRANSPORT_ERROR = "transport_error"
    INVALID_NUMBER = "invalid_number"
    UNKNOWN = "unknown"


class SessionState(StrEnum):
    """Session lifecycle states per data-model.md."""

    CREATED = "created"
    ELIGIBILITY_EVALUATED = "eligibility_evaluated"
    IN_FLIGHT = "in_flight"
    FINALIZED = "finalized"
    BLOCKED = "blocked"


class WriteBackKind(StrEnum):
    """FR-019 idempotency-key write_back_kind enumeration."""

    SESSION_STATE = "session_state"
    NORMALIZED_RESULT = "normalized_result"
    ATTEMPT_COUNT = "attempt_count"
    PHONE_CALL_ACTIVITY = "phone_call_activity"
    QUEUE_STATUS_UPDATE = "queue_status_update"
    TASK_PAYLOAD = "task_payload"
    EXPORTED_ARTIFACT = "exported_artifact"


# Type alias for FR-004 single-letter rule code.
RuleCode = Literal["a", "b", "c", "d", "e", "f"]

# ISO 8601 UTC ms timestamp string per FR-014. Pattern: 2026-05-19T17:00:00.000Z
UtcMs = Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")]

# Slice 1 schema version tag (research.md §Schema versioning).
SCHEMA_VERSION = "slice1-v1"


# ---------------------------------------------------------------------------
# Core entities
# ---------------------------------------------------------------------------


class QueueItem(BaseModel):
    """FR-002 + Clarifications Round 2 Q18 — local ALF prospect record."""

    model_config = ConfigDict(extra="forbid")

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
    """FR-004 + FR-005 — per-record eligibility outcome."""

    model_config = ConfigDict(extra="forbid")

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
    failing_rules: list[RuleCode] = Field(default_factory=list)
    default_tz_applied: bool = False  # True when the configured default tz was substituted
    default_tz_substituted_for: str | None = None
    session_id: str


class Session(BaseModel):
    """FR-005 + FR-012 + FR-013 — one end-to-end run on a queue item."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    queue_item_id: str
    persona_version: str | None = None
    state: SessionState
    final_disposition: Disposition | None = None
    blocked_reason: list[RuleCode] | None = None
    mock_provider_call_id: str | None = None
    started_at: UtcMs
    ended_at: UtcMs | None = None


# FR-024 ("exported artifacts MUST NOT contain secrets / minimize sensitive data") +
# Clarifications Round 2 Q15 — per-event-type payload sub-schema. Keys outside the set
# for an event type are dropped on construction so exported artifacts (notably
# conflicting-events.json, which serialises payloads verbatim) never carry unexpected or
# sensitive data. Dropping (rather than raising on) unknown keys keeps a future provider
# that adds fields forward-compatible.
_ALLOWED_PAYLOAD_KEYS: dict[EventType, frozenset[str]] = {
    EventType.CONNECTED: frozenset(),
    EventType.NO_ANSWER: frozenset(),
    EventType.COMPLETED: frozenset(),
    EventType.VOICEMAIL: frozenset({"voicemail_length_seconds"}),
    EventType.FAILED: frozenset({"failure_reason"}),
    EventType.CALLBACK_REQUESTED: frozenset({"window_hint"}),
}

# Q15 — expected value type for each known payload key. Once unknown keys are
# stripped, retained values are checked so a malformed fixture (a non-int voicemail
# length, an unrecognised failure_reason) fails validation rather than being
# persisted/exported as valid. A StrEnum entry validates enum membership.
_PAYLOAD_KEY_TYPES: dict[str, type] = {
    "voicemail_length_seconds": int,
    "failure_reason": FailureReason,
    "window_hint": str,
}


class MockCallEvent(BaseModel):
    """FR-006 + Clarifications Round 2 Q15 — one transport-emitted event."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    event_id: str
    event_type: EventType
    received_at: UtcMs
    payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _allowlist_payload_keys(self) -> MockCallEvent:
        """FR-024 + Q15 — retain only the payload keys this event type is defined to
        carry, and reject any retained value whose type does not match the schema."""
        allowed = _ALLOWED_PAYLOAD_KEYS.get(self.event_type, frozenset())
        filtered = {k: v for k, v in self.payload.items() if k in allowed}
        for key, value in filtered.items():
            expected = _PAYLOAD_KEY_TYPES.get(key)
            # `None` is an allowed "not provided" marker for any key; a present
            # non-null value must match the schema type / enum.
            if expected is None or value is None:
                continue
            if issubclass(expected, StrEnum):
                allowed_values = sorted(m.value for m in expected)
                if value not in allowed_values:
                    raise ValueError(
                        f"payload key {key!r} must be one of {allowed_values}, got {value!r}"
                    )
            elif not isinstance(value, expected):
                raise ValueError(
                    f"payload key {key!r} must be {expected.__name__}, got {type(value).__name__}"
                )
        if len(filtered) != len(self.payload):
            self.payload = filtered
        return self


# ---------------------------------------------------------------------------
# Persona extraction (FR-034)
# ---------------------------------------------------------------------------


class Extraction(BaseModel):
    """FR-034 — what the persona extracts from a connected conversation."""

    model_config = ConfigDict(extra="forbid")

    captured_email: str | None = None
    captured_email_unverified: str | None = None
    callback_requested: bool = False
    preferred_callback_window: str | None = None
    role_confidence: RoleConfidence
    intent_classification: IntentClassification
    refusal_topics: list[RefusalTopic] = Field(default_factory=list)

    @model_validator(mode="after")
    def _exclusive_email_fields(self) -> Extraction:
        if self.captured_email is not None and self.captured_email_unverified is not None:
            raise ValueError("captured_email and captured_email_unverified are mutually exclusive")
        return self


# ---------------------------------------------------------------------------
# Normalized result (FR-014) — the canonical persona output for a session
# ---------------------------------------------------------------------------


class NormalizedResult(BaseModel):
    """FR-014 — exported as session-result.json."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["slice1-v1"] = SCHEMA_VERSION
    session_id: str
    queue_item_id: str
    mock_provider_call_id: str | None = None
    persona_version: str | None = None
    final_disposition: Disposition
    summary: str | None = Field(default=None, max_length=200)
    transcript_pointer: str | None = None
    captured_email: str | None = None
    captured_email_unverified: str | None = None
    callback_requested: bool = False
    preferred_callback_window: str | None = None
    human_review_reason: HumanReviewReason | None = None
    blocked_reason: list[RuleCode] | None = None
    started_at: UtcMs
    ended_at: UtcMs

    @model_validator(mode="after")
    def _exclusive_email_fields(self) -> NormalizedResult:
        if self.captured_email is not None and self.captured_email_unverified is not None:
            raise ValueError("captured_email and captured_email_unverified are mutually exclusive")
        return self


# ---------------------------------------------------------------------------
# CRM write-back payloads (FR-028 / FR-029 / FR-030)
# ---------------------------------------------------------------------------


class PhoneCallActivityPayload(BaseModel):
    """FR-028 — emitted via writeback.json under `phone_call_activity` key."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["slice1-v1"] = SCHEMA_VERSION
    session_id: str
    queue_item_id: str
    mock_provider_call_id: str
    persona_version: str
    final_disposition: Disposition
    summary: str = Field(max_length=200)
    started_at: UtcMs
    ended_at: UtcMs


class QueueStatusUpdatePayload(BaseModel):
    """FR-029 — always emitted exactly once per session."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["slice1-v1"] = SCHEMA_VERSION
    session_id: str
    queue_item_id: str
    previous_status: CallableStatus
    new_status: CallableStatus
    transition_reason: str
    transition_at: UtcMs


class TaskPayload(BaseModel):
    """FR-030 + Clarifications Round 2 Q19 — emitted only when FR-031 says so."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["slice1-v1"] = SCHEMA_VERSION
    task_id: str
    session_id: str
    queue_item_id: str
    task_kind: Literal["callback", "review"]
    subject: str
    reason_code: HumanReviewReason | None = None  # required when task_kind=='review'
    preferred_callback_window: str | None = None  # required when task_kind=='callback' AND captured
    captured_email: str | None = (
        None  # populated only for callback tasks when verified email present
    )
    assigned_to: str | None = None  # OPTIONAL per Q19; Slice 1 mock leaves null
    persona_version: str
    created_at: UtcMs

    @model_validator(mode="after")
    def _kind_invariants(self) -> TaskPayload:
        # FR-030: review tasks carry a reason_code; callback tasks do not. `captured_email`
        # is a callback-task field (Q5 clarification) and MUST NOT appear on review tasks.
        if self.task_kind == "review":
            if self.reason_code is None:
                raise ValueError("review task requires reason_code")
            if self.captured_email is not None:
                raise ValueError("review task must not carry captured_email")
        else:  # task_kind == "callback"
            if self.reason_code is not None:
                raise ValueError("callback task must not carry reason_code")
        return self


class WriteBack(BaseModel):
    """Composite writeback.json artifact — three sub-payloads grouped per session."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["slice1-v1"] = SCHEMA_VERSION
    session_id: str
    phone_call_activity: PhoneCallActivityPayload | None = None
    queue_status_update: QueueStatusUpdatePayload
    task: TaskPayload | None = None


# ---------------------------------------------------------------------------
# Conflicting late event audit (FR-020)
# ---------------------------------------------------------------------------


class ConflictingEventAuditRecord(BaseModel):
    """FR-020 — one row per rejected late event."""

    model_config = ConfigDict(extra="forbid")

    audit_id: str
    session_id: str
    event_id: str
    conflicting_event_type: EventType
    received_at: UtcMs
    full_event_payload: dict[str, Any] = Field(default_factory=dict)
    preserved_disposition: Disposition


# ---------------------------------------------------------------------------
# Eligibility decision artifact (exported as eligibility-decision.json)
# ---------------------------------------------------------------------------


class ExportedEligibilityDecision(BaseModel):
    """Exported per-session eligibility-decision.json (research.md §Artifact directory)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["slice1-v1"] = SCHEMA_VERSION
    decision_id: str
    queue_item_id: str
    session_id: str
    decided_at: UtcMs
    outcome: Literal["allow", "block"]
    rules: dict[RuleCode, bool]
    failing_rules: list[RuleCode] = Field(default_factory=list)
    default_tz_applied: bool = False  # True when the configured default tz was substituted
    default_tz_substituted_for: str | None = None


# ---------------------------------------------------------------------------
# Slice 1 configuration
# ---------------------------------------------------------------------------


class CallWindowConfig(BaseModel):
    """`[call_window]` section of slice1.toml."""

    model_config = ConfigDict(extra="forbid")

    start: str = Field(pattern=r"^\d{2}:\d{2}$")  # "HH:MM"
    end: str = Field(pattern=r"^\d{2}:\d{2}$")

    @model_validator(mode="after")
    def _validate_hhmm_ranges(self) -> CallWindowConfig:
        """Reject well-formed but out-of-range times (e.g. "99:99"): the field pattern
        only checks the two-digit HH:MM shape, so a bad config would otherwise crash
        eligibility evaluation instead of failing fast at config load."""
        for label, value in (("start", self.start), ("end", self.end)):
            hh, mm = (int(part) for part in value.split(":", 1))
            if not (0 <= hh <= 23 and 0 <= mm <= 59):
                raise ValueError(f"call_window.{label} {value!r} is not a valid HH:MM time")
        return self


class EligibilityConfig(BaseModel):
    """`[eligibility]` section."""

    model_config = ConfigDict(extra="forbid")

    max_attempts: int = Field(ge=1)
    default_timezone: str


class ArtifactsConfig(BaseModel):
    """`[artifacts]` section."""

    model_config = ConfigDict(extra="forbid")

    dir: str
    schema_version: Literal["slice1-v1"] = SCHEMA_VERSION


class PersonaConfig(BaseModel):
    """`[persona]` section."""

    model_config = ConfigDict(extra="forbid")

    version: str


class StateConfig(BaseModel):
    """`[state]` section."""

    model_config = ConfigDict(extra="forbid")

    db: str


class SliceConfig(BaseModel):
    """Root configuration object loaded from slice1.toml + env-var overrides."""

    model_config = ConfigDict(extra="forbid")

    call_window: CallWindowConfig
    eligibility: EligibilityConfig
    artifacts: ArtifactsConfig
    persona: PersonaConfig
    state: StateConfig


# ---------------------------------------------------------------------------
# Slice 2 — Mock Call, Real CRM (data-model.md §4 — additive only)
# ---------------------------------------------------------------------------


class RunMode(StrEnum):
    """FR-031 — CLI run mode. Dry-run is the default; write-enabled needs an explicit flag."""

    DRY_RUN = "dry-run"
    WRITE_ENABLED = "write-enabled"


class RunStatus(StrEnum):
    """`writeback_progress.run_status` — the resume-ledger state (FR-023)."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    RESUME_NEEDED = "resume_needed"
    BLOCKED = "blocked"


class CrmRecordKind(StrEnum):
    """`crm_correlations.record_kind` — the CRM record kinds Slice 2 writes back."""

    PHONE_CALL_ACTIVITY = "phone_call_activity"
    TASK = "task"
    QUEUE_STATUS = "queue_status"


class CrmWriteStatus(StrEnum):
    """`crm_correlations.write_status`."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class CrmCorrelation(BaseModel):
    """FR-024 — local record tying a session to one Dataverse record (mirrors the
    `crm_correlations` table)."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    record_kind: CrmRecordKind
    idempotency_key: str
    dataverse_record_id: str | None = None
    write_status: CrmWriteStatus
    created_at: UtcMs
    updated_at: UtcMs


class WriteBackProgress(BaseModel):
    """FR-023 — the per-session resume ledger (mirrors the `writeback_progress` table)."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    phone_call_activity_done: bool = False
    queue_status_update_done: bool = False
    task_done: bool = False
    run_status: RunStatus
    last_error: str | None = None
    updated_at: UtcMs


class MetadataVerificationReport(BaseModel):
    """FR-001/FR-002 — the result of lightweight live metadata verification."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    missing: list[str] = Field(default_factory=list)
    drift: list[str] = Field(default_factory=list)
    checked_at: UtcMs


class DataQualityWarning(BaseModel):
    """FR-034 — a non-fatal data-quality warning (e.g. a non-E.164 phone number)."""

    model_config = ConfigDict(extra="forbid")

    code: str
    field: str
    message: str


# ---- Dataverse mapping artifact (config/dataverse_mapping.json — data-model.md §2) ----


class DataverseMappingMeta(BaseModel):
    """`_meta` block of the mapping artifact (tolerates documentation keys)."""

    model_config = ConfigDict(extra="ignore")

    schema_version: str
    discovered_at: str
    dataverse_env_url: str
    approved: bool = False


class DataverseEntityRef(BaseModel):
    """One entry of the mapping artifact's `entities` map.

    `entity_set_name` is the Dataverse Web API collection name used in record
    URIs (e.g. `phonecalls` for the `phonecall` table). It defaults to None;
    the adapter falls back to `logical_name + "s"` (plus a curated irregular-
    plural map) only when this is unset. Operators populate `entity_set_name`
    by hand on PR review for any entity whose `EntitySetName` doesn't follow
    that rule. Today `discover-crm` does NOT auto-populate this field — that's
    a follow-on enhancement (read `EntityDefinition.EntitySetName` during
    discovery and write it into the artifact alongside `primary_id`).
    """

    model_config = ConfigDict(extra="ignore")

    logical_name: str
    primary_id: str | None = None
    entity_set_name: str | None = None


class DataverseFieldRef(BaseModel):
    """One entry of the mapping artifact's `fields` map."""

    model_config = ConfigDict(extra="ignore")

    entity: str
    logical_name: str
    type: str
    lookup_target: str | None = None
    approved_update_field: bool = False


class DataverseOptionSetRef(BaseModel):
    """One entry of the mapping artifact's `option_sets` map."""

    model_config = ConfigDict(extra="ignore")

    field: str
    value: int


class DataverseMapping(BaseModel):
    """FR-004 — the documented, verified Dataverse field-mapping artifact."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    meta: DataverseMappingMeta = Field(alias="_meta")
    entities: dict[str, DataverseEntityRef] = Field(default_factory=dict)
    fields: dict[str, DataverseFieldRef] = Field(default_factory=dict)
    option_sets: dict[str, DataverseOptionSetRef] = Field(default_factory=dict)
    task_owner_override_field: str | None = None
    preserve_if_present: list[str] = Field(default_factory=list)


# ---- Slice 2 configuration (config/slice2.toml — data-model.md §3) ----


class RunConfig(BaseModel):
    """`[run]` section of slice2.toml."""

    model_config = ConfigDict(extra="forbid")

    default_mode: RunMode = RunMode.DRY_RUN
    campaign: str = ""


class DataverseConfig(BaseModel):
    """`[dataverse]` section of slice2.toml."""

    model_config = ConfigDict(extra="forbid")

    env_url: str
    mapping_artifact: str
    callable_status: str


class RetryConfig(BaseModel):
    """`[retry]` section — FR-023 bounded-retry tunables."""

    model_config = ConfigDict(extra="forbid")

    max_retries: int = Field(ge=0)
    backoff_seconds: list[float]
    retry_after_cap_seconds: float = Field(gt=0)


class TaskOwnersConfig(BaseModel):
    """`[task_owners]` section — FR-025 default owner per Task kind."""

    model_config = ConfigDict(extra="forbid")

    callback: str
    review: str


class RedactionPolicyConfig(BaseModel):
    """`[redaction]` section (FR-028, FR-029, FR-030)."""

    model_config = ConfigDict(extra="forbid")

    policy: Literal["regex", "noop"] = "regex"
    retention: Literal["full", "summary-only"] = "full"
    patterns: list[str] = Field(default_factory=list)


class Slice2Config(BaseModel):
    """Root non-secret Slice 2 configuration loaded from config/slice2.toml."""

    model_config = ConfigDict(extra="forbid")

    run: RunConfig
    dataverse: DataverseConfig
    retry: RetryConfig
    task_owners: TaskOwnersConfig
    redaction: RedactionPolicyConfig


class DataverseSecrets(BaseModel):
    """Dataverse connection secrets — loaded from environment variables only (FR-005)."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    client_id: str
    client_secret: str
    env_url: str
