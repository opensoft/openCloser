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
        """FR-024 + Q15 — retain only the payload keys this event type is defined to carry."""
        allowed = _ALLOWED_PAYLOAD_KEYS.get(self.event_type, frozenset())
        filtered = {k: v for k, v in self.payload.items() if k in allowed}
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
