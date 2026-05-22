# Open Checklist Questions — Slice 1 (001-mock-call-mock-crm)

**Created**: 2026-05-19
**Status**: Answered — recommendations accepted
**How to use**: Answer each question by editing this file directly. Fill in the `**Your answer**:` line below each question. When done, save and re-invoke `/speckit.implement`.

**Background**: I walked all 15 checklists, ticked 504 of 531 items I could confidently confirm from spec.md / plan.md / research.md / data-model.md / contracts/ / quickstart.md / constitution.md. The remaining 27 items (consolidated below into 21 thematic questions) genuinely need your judgment. Most are product / compliance / framing decisions, not implementation details.

Each question shows:
- **Recommendation**: what I'd pick if asked to default
- **Resolves**: which checklist items it closes
- **Why open**: why I couldn't decide alone

---

## Q1. What does "conceptual contract" mean operationally?

The phrase appears in FR-008 (transport ↔ future SignalWire), FR-016 (CRM adapter ↔ future Dataverse), and across `contracts/*.md`. Is it a named interface file? A method-signature list? A reviewer-judgment phrase?

**Recommendation**: A named language-neutral interface (the public-surface section of each `contracts/*.md`) + a method-signature list. Reviewed against the future SDK's intended methods at Slice 2 plan time. Verified by T075.

**Resolves**: contracts.md CHK016, transport.md CHK009, boundaries.md CHK009, crm-writeback.md CHK011

**Your answer**:
Accept recommendation.


---

## Q2. Should the persona's disclosure language be a verbatim canonical string?

FR-010 says the persona MUST disclose "it is an AI assistant calling on behalf of Medx" in its first utterance. The contracts/persona.md disclosure validator currently checks for two phrases (AI + Medx). Should we pin the exact wording (e.g., "Hi, this is an AI assistant calling on behalf of Medx") or leave it boundary-constrained?

**Recommendation**: Pin an exact canonical wording for Slice 1 to make tests trivially exact: `"Hi, this is an AI assistant calling on behalf of Medx, the senior-living placement service. Is this a good time to chat for two minutes?"` (or your preferred phrasing). Allow paraphrases in future slices only.

**Resolves**: persona.md CHK007

**Your answer**:
Accept recommendation. Use the exact Slice 1 wording:
`Hi, this is an AI assistant calling on behalf of Medx, the senior-living placement service. Is this a good time to chat for two minutes?`


---

## Q3. What "allowed claim categories" can the persona make about Medx?

FR-009 says the persona "owns allowed claims" but the spec doesn't enumerate them. The persona will be making sales claims to ALF prospects, so this affects compliance and brand consistency.

**Recommendation**: Enumerate at category-level (NOT verbatim text): `services_offered` (senior-placement matchmaking), `geographic_coverage` (which markets), `scheduling` (callback windows, availability), `pricing_general` (free-to-prospect; we're paid by partner facilities — actual cost claims forbidden), `next_steps` (callback or email follow-up). Disallowed: specific cost figures, clinical recommendations, comparisons to specific competitors.

**Resolves**: safety.md CHK002, persona.md CHK006

**Your answer**:
Accept recommendation.


---

## Q4. What PHI / disallowed claim categories should be enumerated?

FR-010 says "MUST remain non-clinical, MUST NOT collect resident or patient health information" but doesn't enumerate disallowed data classes or topics.

**Recommendation**: Enumerate explicit PHI examples the persona MUST refuse to collect or discuss: resident names, room numbers, diagnoses, medications, treatment plans, family medical history, dietary restrictions framed as medical, fall-risk scores, cognitive-status indicators, end-of-life plans. Enumerate disallowed topics the persona MUST escalate (`non_clinical_topic_escalation`): clinical advice, legal advice, regulatory interpretations, insurance-coverage disputes, complaints about specific facilities.

**Resolves**: safety.md CHK003, safety.md CHK008

**Your answer**:
Accept recommendation.


---

## Q5. What are the DNC trigger criteria?

FR-010 + FR-036 say the persona must honor DNC immediately when `intent_classification == dnc_stated`, but the trigger conditions aren't enumerated.

**Recommendation**: Trigger on any of: explicit phrase patterns (`"don't call"`, `"stop calling"`, `"take me off"`, `"remove me"`, `"do not contact"`, `"unsubscribe"`, `"opt out"`, `"opt-out"`), OR an "explicit opt-out" intent classification from the persona's extraction (rule-based heuristic in Slice 1, model-based in later slices). Ambiguous statements ("I'm busy", "we'll get back to you", "not interested right now") MUST NOT trigger DNC — those are `not_interested` or `call_back_later`. Truly ambiguous DNC statements MUST escalate to `needs_human_review` with `ambiguous_dnc`.

**Resolves**: safety.md CHK004

**Your answer**:
Accept recommendation.


---

## Q6. Is collecting an email address considered safe for Slice 1?

The persona collects `captured_email` (FR-014, FR-030 carve-out). Is an email address ever PHI? Is consent capture required before persisting?

**Recommendation**: For Slice 1, treat email as non-PHI business contact data. The persona MUST obtain explicit verbal consent ("can I confirm your email address?") + read-back before storing. The Slice 1 verified-email assumption already encodes this. Captured emails MUST NOT be combined with any clinical/health context in the transcript — that's covered by Q4.

**Resolves**: safety.md CHK015

**Your answer**:
Accept recommendation.


---

## Q7. What is the Slice 2 transcript-redaction roadmap?

The Slice 1 Assumptions §Transcript retention accepts the risk that the full scripted transcript is written to disk. Slice 2 needs a redaction layer when real conversations may carry incidental PHI.

**Recommendation**: Slice 2 plan adds a `RedactionLayer` module on the transcript pipeline that runs before disk-write. Default policy: regex + named-entity strip for PHI keywords from Q4's enumeration, replacing with `[REDACTED]`. The redaction layer is OFF in Slice 1 (no real conversation) and ON by default in Slice 2. Configurable per-deployment. Track as a Slice 2 backlog item; no Slice 1 deliverable.

**Resolves**: safety.md CHK040

**Your answer**:
Accept recommendation.


---

## Q8. role_confidence edge case: decision-maker who is uncertain about engaging?

FR-034 enumerates `role_confidence` as `confident_decision_maker` / `confident_non_decision_maker` / `uncertain`. What about a contact who's clearly the decision-maker but uncertain whether they want to engage with Medx specifically?

**Recommendation**: `role_confidence='confident_decision_maker'` is purely about ROLE certainty. Engagement uncertainty is captured by `intent_classification` (`uncertain` or `not_interested` or `call_back_later`). The two fields are independent. So this case maps to `role_confidence='confident_decision_maker'` + `intent_classification='uncertain'` → FR-036 rule #3 → `needs_human_review` with `uncertain_intent`.

**Resolves**: persona.md CHK039

**Your answer**:
Accept recommendation.


---

## Q9. How is `refusal_topics` formatted?

FR-034 includes `refusal_topics` as a list, but doesn't specify whether it's a free-form list of strings or an enumerated set of category labels.

**Recommendation**: Enumerated set of category labels matching the Q4 disallowed-topic categories: `clinical_advice`, `legal_advice`, `regulatory_interpretation`, `insurance_dispute`, `competitor_comparison`, `pricing_specific`, `medical_history`. Free-form is forbidden in Slice 1 to keep the audit story tight.

**Resolves**: persona.md CHK041

**Your answer**:
Accept recommendation.


---

## Q10. What concrete trigger condition fires each FR-035 reason code?

FR-035 enumerates 9 reason codes but doesn't pin "code X fires when…" precisely. Some are obvious (`legal_request` when contact requests a recording be deleted), others overlap (when does `phi_collection_risk` fire vs. `non_clinical_topic_escalation`?).

**Recommendation**: Pin one-line trigger per code in the persona's `escalation.py` module:
- `uncertain_role` — `role_confidence == 'uncertain'`
- `uncertain_intent` — `intent_classification == 'uncertain'` AND `role_confidence != 'uncertain'`
- `ambiguous_dnc` — contact uses DNC-adjacent phrasing the persona can't disambiguate
- `captured_email_invalid_no_callback` — FR-036 rule #7
- `phi_collection_risk` — contact volunteers (or persona detects) any PHI from Q4's enumeration
- `legal_request` — contact requests recording deletion, GDPR-style data access, or legal escalation
- `non_clinical_topic_escalation` — contact asks for clinical/legal/insurance advice the persona can't answer
- `outside_allowed_claims` — contact asks for info outside Q3's allowed-claim categories
- `script_truncated` — fixture ended without producing a disposition (FR-036 rule #10)

**Resolves**: persona.md CHK045

**Your answer**:
Accept recommendation.


---

## Q11. Does the call window apply 7 days a week, or weekdays only?

Configured call window is 9:00 AM – 8:00 PM (Assumptions). Does this apply Monday–Friday only, or every day of the week?

**Recommendation**: Every day of the week for Slice 1 (matches a sales-outreach default). Weekday filtering is configurable in a future slice if needed. Document the choice in `config/slice1.toml` with a comment.

**Resolves**: eligibility.md CHK002

**Your answer**:
Accept recommendation.


---

## Q12. Are the call window boundaries inclusive or exclusive?

Is `09:00:00.000` allowed (inclusive start) and `20:00:00.000` allowed (inclusive end)? Or is the window `[09:00, 20:00)` (start inclusive, end exclusive)?

**Recommendation**: `[09:00, 20:00]` both ends inclusive at minute resolution. A call placed at exactly 8:00 PM local time is allowed; a call placed at 8:01 PM is blocked.

**Resolves**: eligibility.md CHK008

**Your answer**:
Accept recommendation.


---

## Q13. What is the precise definition of "phone presence"?

FR-004(a) says "phone presence" passes eligibility. Is that "non-empty string", "non-null", or stricter (E.164 format, valid country code)?

**Recommendation**: For Slice 1: non-null AND non-empty after trim (no whitespace-only strings). E.164 hard validation is deferred until the real-telephony slice because SignalWire requires it. Document in `eligibility/evaluator.py` rule (a).

**Resolves**: eligibility.md CHK009

**Your answer**:
Accept recommendation.


---

## Q14. How are daylight-saving-time transitions handled mid-call-window?

If the configured window is 9:00–20:00 local time, a DST transition could move the local time in or out of the window for a record. How should Slice 1 handle this?

**Recommendation**: Slice 1 single-record processing makes mid-call DST irrelevant (a call lasts ~minutes, far shorter than a DST transition). The eligibility evaluator MUST use the record's local time at decision time via `zoneinfo` (which handles DST correctly). No special handling needed; documented as an accepted edge case.

**Resolves**: eligibility.md CHK029

**Your answer**:
Accept recommendation.


---

## Q15. What payload sub-schema does each Mock Call Event type carry?

Key Entities mentions "optional payload (e.g., voicemail length, failure reason)" but doesn't enumerate per-event-type schemas.

**Recommendation**: Pin a minimal payload schema per type:
- `connected` — `{}` (no payload; the event is the signal)
- `no_answer` — `{}` (no payload)
- `voicemail` — `{"voicemail_length_seconds": int}` (optional, may be 0)
- `failed` — `{"failure_reason": str}` (one of `carrier_error`, `transport_error`, `invalid_number`, `unknown`)
- `completed` — `{}` (no payload; mirrors successful end of `connected`)
- `callback_requested` — `{"window_hint": str | null}` (the persona-extracted window, if any)

Slice 2 may add fields (e.g., real provider's raw event blob) under a `provider_raw` sub-key.

**Resolves**: data-model.md CHK003, transport.md CHK005

**Your answer**:
Accept recommendation.


---

## Q16. What format is `preferred_callback_window`?

FR-014 lists `preferred_callback_window` as a field. Is it a single timestamp, a `start..end` range, a weekday+hour combo, or free-form?

**Recommendation**: Free-form string for Slice 1 (e.g., `"Thursday 14:00"`, `"tomorrow afternoon"`, `"next Tuesday 2-4 PM"`). The string is what the contact said, preserved verbatim. Structured parsing (timestamp range) deferred to Slice 2 when scheduling integration arrives.

**Resolves**: data-model.md CHK012

**Your answer**:
Accept recommendation.


---

## Q17. What is `summary` (FR-014)?

Is the `summary` field a one-sentence outcome, a bullet list of key facts, or free-form prose?

**Recommendation**: One-sentence outcome, ≤ 200 characters, persona-authored, plain English suitable for a sales-CRM activity feed. Example: `"Decision-maker confirmed interested; callback requested Thursday 14:00; verified email captured."`. Structured fields (callback flag, email, etc.) are separate columns; `summary` is the human-readable headline.

**Resolves**: data-model.md CHK017

**Your answer**:
Accept recommendation.


---

## Q18. What does `last_decision_at` on the Queue Item represent?

Is it the timestamp of the eligibility decision, the session finalization, or "most recent of either"?

**Recommendation**: Most recent of either. Updated by the orchestrator at end-of-run (after session finalization OR eligibility-block). One field, one source of truth, reflects "when this record was last touched by openCloser".

**Resolves**: data-model.md CHK037

**Your answer**:
Accept recommendation.


---

## Q19. Does the Task payload include an owner / assigned-to field?

FR-030 lists `task_kind`, `subject`, `reason_code`, etc., but no owner. Real-world CRM tasks have an owner.

**Recommendation**: Add `assigned_to` as an optional field on Task payload. For Slice 1 mock, set to `null` (no real users to assign to). For Slice 2 Dataverse, populated from a configurable default-owner mapping per task_kind. Document in FR-030 as optional.

**Resolves**: crm-writeback.md CHK010

**Your answer**:
Accept recommendation.


---

## Q20. What format pins FR-033's "language-neutral interface"?

FR-033 says the contract surfaces MUST be language-neutral. Is the format `contracts/*.md` pseudo-code (what we have now), Pydantic class names, Python ABCs, OR a separate `.pyi` interface file?

**Recommendation**: Markdown pseudo-code in `contracts/*.md` is the canonical format for Slice 1 (already in place). Python ABCs in `src/opencloser/<module>/base.py` are the runtime enforcement. The Slice 2 plan-time review (T075) verifies the markdown pseudo-code against the real SDK shapes. No `.pyi` files needed unless a future cross-language port is planned.

**Resolves**: boundaries.md CHK038

**Your answer**:
Accept recommendation.


---

## Q21. Is markdown pseudo-code in `contracts/*.md` "language-neutral enough"?

The contract files use Python-flavored pseudo-code (`session_context: SessionContext`). Is that acceptable as "language-neutral" per FR-033, or should we strip Python type-annotation syntax?

**Recommendation**: Acceptable as-is. The pseudo-code uses Python-style type hints because Python is Slice 1's implementation language and the hints are widely-readable across languages (TypeScript and Kotlin developers will recognize `name: Type`). The contracts' AUTHORITY is the prose description of operations + inputs + outputs; the type-hint syntax is decorative. Document this stance in a one-line note at the top of each contract file.

**Resolves**: contracts.md CHK013

**Your answer**:
Accept recommendation.


---

## Summary

- **21 thematic questions** consolidating 27 unchecked checklist items
- Each has a **default recommendation** you can accept by replying `recommended` or `yes`
- You can also reply with a free-form answer for any question

**When done**: save this file and re-invoke `/speckit.implement` (or just say "answers are in"). I'll:
1. Read your answers from this file
2. Apply them as spec/plan amendments where appropriate
3. Tick the corresponding checklist items
4. Re-run the checklist gate (should pass cleanly)
5. Begin Phase 1 of tasks.md

If you want me to take every recommendation without reviewing, just say "recommended for all" — I'll apply, tick, and start implementation immediately.

---

## Quick links

- Spec: [spec.md](./spec.md)
- Plan: [plan.md](./plan.md)
- Tasks: [tasks.md](./tasks.md)
- Constitution: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md)
- Quickstart: [quickstart.md](./quickstart.md)
