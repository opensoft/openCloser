# Slice 3 — Real Call, Real CRM — Clarification Questions

**Feature**: 003-real-call-real-crm
**Session**: 2026-05-25
**Spec**: `specs/003-real-call-real-crm/spec.md`

## Coverage scan summary

| Category | Status | Notes |
|---|---|---|
| Functional Scope & Behavior | Clear | Goals, in/out-of-scope, run modes explicit |
| Domain & Data Model | Clear | Entities + renames documented |
| Interaction & UX Flow | Clear | CLI w/ explicit real-call flag |
| NFR — Performance | Resolved | Q4 answered: degradation triggers include provider error, Pipecat runtime crash, and configurable silence-after-connection timeout |
| NFR — Reliability | Resolved | Q5 answered: concurrent same-item invocation reuses Slice 2 queue-claim blocking semantics |
| NFR — Observability | Resolved | Q3 answered: operator identity is captured locally on session and run report only |
| NFR — Security & Privacy | Resolved | Q1 answered: implicit acknowledgment after disclosure when no opt-out; Q2 answered: raw-audio capture deferred out of Slice 3 |
| NFR — Compliance | Clear | Non-clinical, no-PHI explicit |
| Integration & External Dependencies | Clear | SignalWire / Pipecat / live model / shadow STT bounded |
| Edge Cases & Failure Handling | Resolved | Q4 answered: no usable signal includes configurable silence-after-connection timeout |
| Constraints & Tradeoffs | Clear | Slice 1 / Slice 2 contract preservation explicit |
| Terminology & Consistency | Clear | Renames catalogued |
| Completion Signals | Clear | SCs measurable |
| Misc / Placeholders | Clear | Deferred-to-plan list explicit |

---

## Question 1 — Caller consent / disclosure acknowledgment behavior

**Recommended:** Option A — Matches typical AI-disclosure regulatory practice for non-clinical outbound business calls (notice required, affirmative verbal consent not required) and avoids excessive false escalations on connected calls where callers commonly continue without explicit acknowledgment.

After the persona delivers the canonical AI-on-behalf-of-Medx disclosure (FR-015), what is the required behavior when the caller does NOT explicitly acknowledge it (silence, an ambiguous "uh-huh", or proceeds straight to a question)?

| Option | Description |
|--------|-------------|
| A | Continue the persona flow after a brief pause; treat absence of an opt-out as implicit acknowledgment (current behavior is undocumented but implied) |
| B | Require an explicit verbal acknowledgment; if not received within a configured window, escalate `needs_human_review` with a new reason `disclosure_unacknowledged` |
| C | Continue, but record a `disclosure_unacknowledged` audit flag on the session for review (no disposition change, no escalation) |
| D | Defer the policy to the persona module configuration; spec only requires that the chosen policy is recorded on each session for audit |

You can reply with the option letter (e.g., "A"), accept the recommendation by saying "yes" or "recommended", or provide your own short answer.

**Answer:** Option A - Continue the persona flow after a brief pause; treat absence of an opt-out as implicit acknowledgment.

---

## Question 2 — Raw call audio recording (in addition to transcripts)

**Recommended:** Option D — Slice 3's stated scope is real-call + real-CRM proof; raw-audio storage adds non-trivial storage / retention / redaction / regulatory-consent surface area, and the existing transcript artifacts already satisfy FR-036 operator evidence and the FR-035 no-secrets guarantee. Defer until a concrete driver (regulatory dispute, QA pipeline) appears.

Slice 3 mandates transcripts (live + shadow STT) and three retention modes. Should the system also persist the raw call audio as a separate artifact?

| Option | Description |
|--------|-------------|
| A | No raw-audio capture in Slice 3; transcripts only (FR-033 retention modes apply unchanged) |
| B | Raw audio captured by default on every connected real call; honors the same three retention modes as the live transcript |
| C | Raw audio captured only when deployment-configured to do so (opt-in flag); default off; honors the same retention modes when enabled |
| D | Out of scope for Slice 3; defer raw-audio capture to a later slice with its own retention / consent / redaction design |

You can reply with the option letter (e.g., "A"), accept the recommendation by saying "yes" or "recommended", or provide your own short answer.

**Answer:** Option D - Raw-audio capture is out of scope for Slice 3 and deferred to a later slice with its own retention, consent, and redaction design.

---

## Question 3 — Operator identity capture for real-call / write-enabled runs

**Recommended:** Option A — Local capture preserves audit traceability without expanding the Slice 2 Dataverse mapping surface or risking inadvertent PII leak into Dynamics; meets the audit needs in FR-036 while keeping the Slice 1 / Slice 2 Dataverse contract unchanged (FR-020).

Should the invoking operator's identity be recorded for every real-call / write-enabled run?

| Option | Description |
|--------|-------------|
| A | Capture operator identity (OS user / CLI-provided operator id) on the local session + run report only — not propagated into Dynamics |
| B | Capture operator identity on session + run report + the Phone Call activity description (or a mapped Dataverse field) when the mapping artifact supports it |
| C | Do not capture operator identity in Slice 3; rely on shell history and the existing CRM correlation identifiers |
| D | Defer to plan; require only that whatever identity propagation is chosen is consistent across run report + audit artifacts |

You can reply with the option letter (e.g., "A"), accept the recommendation by saying "yes" or "recommended", or provide your own short answer.

**Answer:** Option A - Capture the invoking operator identity on the local session and run report only; do not propagate it into Dynamics.

---

## Question 4 — Live runtime / model degradation detection ("no usable signal" trigger)

**Recommended:** Option B — Matches the spec's "fails or returns no usable signal" language in Story 5 #5; a configurable silence threshold catches the live-model-stuck case that wouldn't surface as an explicit error, while provider errors and runtime crashes still fast-fail without waiting for the timeout.

User Story 5 #5 and FR-013 reference the live Pipecat runtime / configured real-time AI provider "failing or returning no usable signal" mid-call, but the detection trigger is undefined. Which signal MUST trigger orchestrator finalization with `needs_human_review` (`script_truncated`) or `failed` (runtime-failure reason)?

| Option | Description |
|--------|-------------|
| A | Configurable silence / no-extraction-event timeout after call connection only |
| B | Any of: provider error from the configured real-time AI model, Pipecat runtime crash, OR configurable silence-after-connection timeout |
| C | Provider error or runtime crash only; silence alone is not a runtime-degradation signal in Slice 3 |
| D | Defer specific detection signals to plan; the spec fixes only the disposition mapping (silence → `script_truncated`; provider error / crash → `failed`) |

You can reply with the option letter (e.g., "A"), accept the recommendation by saying "yes" or "recommended", or provide your own short answer.

**Answer:** Option B - Treat any real-time AI provider error, Pipecat runtime crash, or configurable silence-after-connection timeout as a live-runtime degradation trigger.

---

## Question 5 — Concurrent CLI invocation on the same Dataverse queue item

**Recommended:** Option A — Aligns with the constitution's "no parallel campaign UI / no multi-worker coordination" stance while still preventing a duplicate real dial. Reuses Slice 2 queue-claim semantics verbatim and is the only option that satisfies SC-008 (no duplicate write-back) without first paying the cost of an unwanted second SignalWire dial.

FR-003 says one queue item per invocation but does not pin behavior when two CLI invocations target the same queue item simultaneously. What behavior is required?

| Option | Description |
|--------|-------------|
| A | Reuse Slice 2 queue-claim semantics: the second invocation observes the item as not-`ready` (claimed / `in_progress`) and exits with a blocked-by-claim message — no dial, no attempt consumed |
| B | Allow both invocations to proceed; rely on Dataverse idempotency-key stamping to dedupe write-back (one unavoidable extra SignalWire dial is accepted) |
| C | Require an explicit operator override flag to re-invoke against any item observed as `in_progress`; default-block otherwise |
| D | Defer to plan; concurrency is operator discipline in Slice 3, not a system contract |

You can reply with the option letter (e.g., "A"), accept the recommendation by saying "yes" or "recommended", or provide your own short answer.

**Answer:** Option A - Reuse Slice 2 queue-claim semantics; a second concurrent invocation exits blocked-by-claim with no dial and no attempt consumed.

---

## Answers recorded

- Q1: Option A - Continue after a brief pause; no explicit disclosure acknowledgment is required when there is no opt-out.
- Q2: Option D - Raw-audio capture is out of scope for Slice 3; defer it to a later slice with dedicated retention, consent, and redaction design.
- Q3: Option A - Record operator identity locally on the session and run report only; do not propagate it into Dynamics.
- Q4: Option B - Provider errors, Pipecat runtime crashes, or configurable silence-after-connection timeout all trigger live-runtime degradation handling.
- Q5: Option A - Reuse Slice 2 queue-claim semantics; concurrent second invocation exits blocked-by-claim with no dial and no attempt consumed.

## Coverage after answers

| Category | Status | Resolution |
|---|---|---|
| NFR - Performance | Resolved | Q4 pins live-runtime degradation triggers, including configurable silence-after-connection timeout. |
| NFR - Reliability | Resolved | Q5 pins concurrent same-item invocation behavior to Slice 2 claim semantics. |
| NFR - Observability | Resolved | Q3 pins operator identity capture to local session and run report. |
| NFR - Security & Privacy | Resolved | Q1 pins disclosure acknowledgment behavior; Q2 excludes raw-audio capture from Slice 3. |
| Edge Cases & Failure Handling | Resolved | Q4 pins no-usable-signal handling triggers. |

---

# Round 2 — Checklist-Driven Clarifications

**Triggered by**: `/speckit-checklist` (max coverage / max depth) surfacing 4 [Conflict] markers and several high-impact [Gap] clusters in `security.md` (19 gaps), `performance.md` (27 gaps — bundled into a Deferred-to-Plan addition; no questions needed), and the cross-cutting `requirements.md`.

**Pre-applied without questions**:
- **CHK012 (observability.md)** — FR-036 now lists `telephony_readiness_summary` and "any failure or blocked reason" to match the Key Entities Run Report description.
- **Performance bundle (27+ gaps)** — added a "Performance and latency targets" subsection under Deferred to Implementation Plan that explicitly acknowledges Slice 3 does not pin numeric latency / throughput / wall-clock targets.

The 9 questions below cover the remaining 3 conflicts and the highest-impact security / safety / reliability gap clusters. Recommendations are stated; reply with letters, `yes` to accept recommendations, or a short free-form alternative per question.

---

## Question 6 — Resume after `answered` callback but no terminal event (Conflict between FR-022 resume and FR-026 abandonment)

**Recommended:** Option B — preserves the FR-026 abandonment contract (no in-progress queue items stuck indefinitely) while reusing Slice 2 resume semantics for the partial write-back; matches the spirit of "abandonment if no terminal event within timeout" without requiring the resume to wait for a callback that may never arrive.

A SignalWire session received the `answered` callback, then the orchestrator process died (or callback delivery failed persistently) before any normalized terminal event arrived. The operator re-invokes the CLI to resume. What is the required behavior?

| Option | Description |
|--------|-------------|
| A | Resume attempts to reconnect to SignalWire callback delivery and continue the in-flight call; finalize only on a real terminal event or after the abandonment timeout elapses from the resume moment |
| B | Resume immediately finalizes the session as `failed` with reason `live_call_abandonment` (the call has been silent past the abandonment timeout by the time a human notices); apply the Slice 2 resume contract for any partial write-back |
| C | Resume waits until the configured live-call abandonment timeout elapses (measured from the original `answered` callback) before finalizing; if the timeout has already elapsed by re-invocation, finalize immediately |

**Answer:** Option B - Resume immediately finalizes as `failed` with reason `live_call_abandonment`; apply Slice 2 resume semantics for any partial write-back.

---

## Question 7 — Shadow STT lane vs. orchestrator finalization timing (Conflict between FR-029 non-blocking and FR-031 escalation)

**Recommended:** Option B — preserves FR-029's strict non-blocking guarantee (no live-call delay) while still giving the shadow lane a bounded post-finalization window to emit a discrepancy. Pending comparisons that exceed the grace window become a `[shadow_lane_truncated]` audit record rather than silently dropped — auditable, but doesn't gate finalization or the CRM write-back.

At the moment the orchestrator wants to finalize a connected-call session, the shadow STT lane may still be processing the tail end of the call. What is the required behavior?

| Option | Description |
|--------|-------------|
| A | Orchestrator finalizes immediately and writes back to CRM; any later shadow-discrepancy event for that session is recorded as a post-finalization audit-only record and never escalates the disposition (no second CRM write) |
| B | Orchestrator finalizes immediately but holds the CRM write-back for a deployment-configurable grace window (e.g., a few seconds) to give the shadow lane a chance to emit a discrepancy in time to participate in the disposition; if the window elapses, write back without it |
| C | Orchestrator waits for shadow lane to drain before finalizing (relaxes FR-029 from "must not block the live call" to allow blocking finalization specifically); never miss a shadow discrepancy |
| D | Defer to deployment configuration (any of A / B / C is configurable); spec only requires that the chosen behavior is recorded on each session |

**Answer:** Option B - Finalize immediately but hold CRM write-back for a configurable grace window so shadow STT can participate if it completes in time; otherwise write back without it.

---

## Question 8 — "Four Slice 2 write-back operations" vs. DNC / blocked-status / opt-out writes (Conflict in FR-020 invariant)

**Recommended:** Option A — preserves the Slice 2 contract verbatim (no new operation count); DNC / opt-out / blocked-status writes are simply the queue-status-update operation parameterized by the relevant disposition's mapping. Avoids inflating the operation surface and stays consistent with FR-021's idempotency-key stamping (which targets Phone Call activity and Task — not queue-status writes).

The spec says (FR-020) the Dataverse write-back adapter has "the same four write-back operations" as Slice 2: Phone Call activity emission, queue-status update emission, Task emission, write-back assembly. But Slice 3 also writes DNC / opt-out fields (FR-024), blocked-status fields (FR-023), and dial-blocked status updates (FR-012). Are these:

| Option | Description |
|--------|-------------|
| A | An explicit subset of the existing "queue-status update emission" operation; the four-operation count is unchanged; DNC / blocked / dial-blocked writes are field-level variants of the queue-status update payload |
| B | Two additional operations bringing the total to six (DNC/opt-out emission, blocked-status emission); update FR-020 and the Key Entities count |
| C | DNC / opt-out is its own operation (DNC-priority semantics — see Q9); blocked-status remains a field on the queue-status update |
| D | Leave the language untouched (accept the ambiguity); add a note in Definitions clarifying the count |

**Answer:** Option A - DNC / opt-out / blocked / dial-blocked writes are field-level variants of the existing queue-status update emission; the four-operation count is unchanged.

---

## Question 9 — SignalWire callback authentication: rejected-callback behavior (Security gap cluster CHK004 / CHK005 / CHK009 / CHK010 / CHK055–CHK058)

**Recommended:** Option B — produces an audit trail of attempted forgeries (a real security signal), distinguishes them from benign duplicates, and surfaces a count to the operator without leaking secrets. Option A loses operator-visible signal; Option C loses the duplicate/forgery distinction; Option D pushes a baseline security policy to deployment.

What is the required behavior for a SignalWire callback that fails authentication (FR-008: "MUST reject callbacks that fail authentication")?

| Option | Description |
|--------|-------------|
| A | Reject at the transport layer with the provider-appropriate HTTP code; do NOT write to the callbacks audit log; do NOT count in the run report |
| B | Reject with the provider-appropriate HTTP code; record in a distinct "rejected-by-authentication" audit log (separate from the duplicate-callback log) with `(received_at, source_ip_or_provider_metadata)` but NOT the verification secret and NOT the callback body content; surface a rejected-by-authentication count in the run report |
| C | Reject and record in the same callbacks audit log as duplicates / out-of-order events, tagged with a `rejected_by_authentication` reason; surface a count in the run report |
| D | Defer to deployment configuration; spec only requires that the rejection MUST NOT leak secrets and MUST be recorded somewhere visible to the operator |

**Answer:** Option B - Reject unauthenticated callbacks, record a distinct rejected-by-authentication audit entry without secrets or callback body content, and surface the count in the run report.

---

## Question 10 — Redaction coverage across all derivative artifacts (Security gap cluster CHK025 / CHK026 / CHK027 / CHK029)

**Recommended:** Option B — closes the highest-value redaction gaps surfaced by the checklist while keeping pointer-only retention auditable (pointer metadata excluded from redaction because pointers must remain machine-readable). Option C preserves status quo (transcript-only) and leaves derivative-artifact redaction implicit; Option A is too broad and would corrupt machine-readable pointer formats.

Default-on transcript redaction (FR-033) clearly applies to the full transcript file. The checklist surfaced ambiguity about other artifacts that may contain the same sensitive content. Which artifacts MUST the default-on redaction policy cover?

| Option | Description |
|--------|-------------|
| A | All derivative artifacts: full transcript + session-result `summary` + shadow STT transcript + shadow STT discrepancy records + transcript pointer metadata + run report excerpts |
| B | Full transcript + session-result `summary` + shadow STT transcript + shadow STT discrepancy records (excluding the transcript pointer itself — pointers must remain machine-readable for resume / inspection) |
| C | Only the full transcript file (status quo — derivative artifacts are not redacted by default; deployment can configure them) |
| D | Defer to deployment configuration with a documented default that matches Option B; spec states only that any sensitive content extracted into a derivative artifact MUST honor the same retention + redaction policy as the originating transcript |

**Answer:** Option B - Default-on redaction covers full transcript, session-result summary, shadow STT transcript, and shadow STT discrepancy records, excluding machine-readable transcript pointers.

---

## Question 11 — PHI artifact-level guarantee (Security gap cluster CHK036 / CHK037; persona-safety overlap)

**Recommended:** Option C — preserves the persona-level no-collection guarantee + adds an artifact-level redaction safety net for the caller-volunteered case + escalates to human review (matches the Slice 1 `phi_collection_risk` escalation pattern, doesn't depend on persona behavior to enforce artifact-level guarantee). Option A is too permissive (PHI in audit artifacts); Option B is too aggressive (always end the call may surprise callers who shared incidental info).

A caller volunteers PHI mid-call (despite the persona refusing to ask for or accept it). What is the required behavior at the artifact level?

| Option | Description |
|--------|-------------|
| A | Persona's no-collection guarantee is sufficient; raw caller utterances are retained verbatim subject to the transcript retention mode (full / summary / pointer) and default-on redaction; no special PHI-volunteered handling |
| B | Persona MUST immediately escalate `needs_human_review` with reason `phi_collection_risk` and end the call; no transcript content past the PHI utterance is written |
| C | Persona MUST escalate `needs_human_review` with reason `phi_collection_risk` AND the default-on redaction policy MUST tag and redact the PHI-bearing utterance in the transcript / summary / shadow transcript / discrepancy records before the artifact is written; the call MAY continue or end per the persona's existing decision rules |
| D | Defer to deployment configuration; spec only requires that PHI-volunteered cases be observably handled differently from non-PHI cases |

**Answer:** Option C - Escalate PHI-volunteered calls to `needs_human_review` with `phi_collection_risk` and redact PHI-bearing content before writing transcript, summary, shadow transcript, or discrepancy artifacts.

---

## Question 12 — Resume-session operator identity (Security gap cluster CHK045 / CHK073)

**Recommended:** Option B — preserves the original operator's audit trail (the person who authorized the real call), records the resuming operator separately on the run report (auditability), and still requires the real-call flag on resume (no implicit promotion). Option A is too restrictive operationally; Option C loses the original-authorizer audit trail.

When operator A initiates a Slice 3 real-call run that partially writes back, and operator B later re-invokes the CLI to resume the same session, what is the required behavior?

| Option | Description |
|--------|-------------|
| A | Resume requires the SAME operator identity as the original invocation; if a different operator attempts the resume, refuse with an operator-mismatch message |
| B | Resume preserves the original session's operator identity on the local session record + audit artifacts; the resuming operator's identity is also recorded on the run report (as "resumed by X, original operator Y"); resume still requires the real-call / write-enabled flag |
| C | Resume accepts any operator; only the resuming operator's identity is recorded on the run report; the original operator identity is overwritten |
| D | Defer to deployment configuration |

**Answer:** Option B - Preserve the original operator identity on the session and audit artifacts, record the resuming operator separately in the run report, and still require the real-call / write-enabled flag.

---

## Question 13 — Real-call flag through retry / resume / callback delivery (Security gap CHK052)

**Recommended:** Option A — keeps the real-call flag as a per-invocation authorization gate (every CLI invocation must explicitly opt in), prevents any path from implicitly promoting a rehearsal-mode session to real-call-mode mid-life, and matches FR-001's spirit ("requires an explicit flag or equivalent deliberate action; default invocation MUST NOT place a call or mutate Dynamics").

The real-call / write-enabled flag is required on the initial invocation (FR-001). The checklist asks whether the flag is also required on every CLI re-invocation that resumes or recovers from a partial write-back. What is the required behavior?

| Option | Description |
|--------|-------------|
| A | The real-call / write-enabled flag MUST be supplied on every CLI invocation that performs a Dataverse mutation, including resume; absence of the flag on resume runs the resume in rehearsal mode (which is a no-op for mutations and surfaces what would have been written) |
| B | The real-call flag is "sticky" on the session: once a session was started in real-call mode, subsequent resumes are auto-elevated to real-call mode without the flag |
| C | The real-call flag is required only on the initial invocation; resume inherits the flag from the session's recorded state |

**Answer:** Option A - Require the real-call / write-enabled flag on every CLI invocation that performs Dataverse mutation, including resume; without it, resume runs in rehearsal/no-mutation mode.

---

## Question 14 — DNC / opt-out write priority on partial-write-back failure (Security gap CHK082)

**Recommended:** Option A — honors the safety-and-human-handoff constitution principle ("immediate stop on clear opt-out or DNC statements") at the artifact level too; ensures opt-out is reflected in the CRM before a less-critical Phone Call activity write, so a partial failure that loses everything BUT the DNC still leaves the contact protected. Idempotency-key stamping prevents duplicate DNC writes on retry.

When a real-call session reaches `do_not_call` (or mid-call opt-out) and the bounded retry budget is exhausted before all write-back operations complete, what is the required write order?

| Option | Description |
|--------|-------------|
| A | DNC / opt-out field write (FR-024) MUST be attempted FIRST in the write-back sequence — before the queue-status update, before the Phone Call activity, before any Task; if it succeeds and everything else fails, the contact is still protected from further outreach |
| B | DNC follows the existing per-disposition write-back order (no priority); rely on idempotency + resume to eventually persist; partial-failure window may leave a contact still callable until resume runs |
| C | DNC write is non-deferrable; if any DNC-related write fails, the run MUST be marked as `needs_human_review` with reason `dnc_write_failure` and a review Task created locally before the run exits |
| D | Defer to deployment configuration; spec only requires that DNC SHOULD complete before less-safety-critical writes |

**Answer:** Option A - Attempt the DNC / opt-out field write first in the write-back sequence before less safety-critical writes.

---

## Round 2 answers recorded

- Q6: Option B - Resume immediately finalizes answered-but-nonterminal sessions as `failed` / `live_call_abandonment` and then uses Slice 2 resume semantics for partial write-back.
- Q7: Option B - Finalization does not wait for shadow STT, but CRM write-back can pause for a configurable grace window; late/missing shadow output becomes audit evidence rather than a live-call blocker.
- Q8: Option A - DNC / opt-out / blocked / dial-blocked writes are field-level variants of the existing queue-status update operation; the write-back operation count remains unchanged.
- Q9: Option B - Authentication-rejected callbacks are rejected, recorded in a distinct no-secret audit log, and counted in the run report.
- Q10: Option B - Default-on redaction covers transcript-derived human-readable artifacts while excluding machine-readable transcript pointers.
- Q11: Option C - Caller-volunteered PHI triggers `phi_collection_risk` review and redaction before any affected transcript, summary, shadow transcript, or discrepancy artifact is written.
- Q12: Option B - Resume preserves original operator identity, records the resuming operator separately, and still requires the real-call / write-enabled flag.
- Q13: Option A - Any mutation-capable invocation, including resume, must explicitly include the real-call / write-enabled flag; otherwise it stays rehearsal/no-mutation.
- Q14: Option A - DNC / opt-out writes are attempted first on `do_not_call` outcomes so the contact is protected even if later write-back steps fail.

## Round 2 coverage after answers

| Category | Status | Resolution |
|---|---|---|
| Reliability | Resolved | Q6, Q7, Q12, and Q13 pin resume, shadow-STT finalization, operator identity on resume, and real-call flag behavior. |
| Security | Resolved | Q9, Q10, Q11, and Q13 pin callback-auth rejection, redaction scope, PHI artifact handling, and mutation authorization. |
| Safety / DNC | Resolved | Q8 and Q14 pin DNC writes as queue-status variants and prioritize opt-out persistence before less critical write-back. |
| Contract Consistency | Resolved | Q8 preserves the Slice 2 four-operation write-back contract while clarifying field-level write variants. |
