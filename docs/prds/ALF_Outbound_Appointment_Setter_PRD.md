# ALF Outbound Appointment Setter PRD

Status: Draft

Parent PRD: [openCloser PRD](./openCloser_PRD.md)

Last updated: 2026-05-19

## Summary

The ALF Outbound Appointment Setter is the first production-oriented slice of openCloser. It calls assisted living facilities from Dynamics 365 Sales Hub, asks whether the facility is interested in Medx services, verifies or captures an email address, and creates a human callback task when interest is detected.

This feature proves the core openCloser loop:

CRM queue -> compliance gate -> outbound call -> AI conversation -> structured disposition -> CRM write-back -> human follow-up.

## MVP Boundary

The MVP for this feature is defined in [openCloser MVP](./openCloser_MVP.md). The smallest useful slice is one campaign, one queued facility record at a time, one ALF appointment-setter persona, and one structured write-back path. Real CRM write-back is proven before real telephony because the CRM loop is expected to be easier and more useful to validate first.

Build slices:

1. Mock call, mock CRM.
2. Mock call, real CRM.
3. Real call, real CRM.

The MVP intentionally excludes multi-provider support, app voice/video, nurse and doctor personas, real scheduling integration, Opportunity creation, campaign UI, advanced analytics, and clinical workflows.

## Users

- Sales operator: prepares CRM lists and monitors campaign outcomes.
- Human callback owner: receives callback tasks for interested facilities.
- Admin/developer: configures provider credentials, queue mappings, and persona behavior.
- Facility staff member: receives the call and answers basic interest and contact questions.

## Goals

- Reduce manual first-touch calling for Medx ALF outreach.
- Keep Dynamics 365 as the operational source of truth.
- Capture structured outcomes from each call.
- Create reliable follow-up tasks for interested facilities.
- Avoid calling facilities at inappropriate times or after opt-out.
- Keep the AI conversation bounded, transparent, and non-clinical.

## Non-Goals

- Negotiating contracts.
- Giving clinical advice.
- Collecting resident or patient PHI.
- Creating a full campaign-management UI.
- Replacing a human sales callback.
- Handling inbound callbacks in the first release.

## Primary Workflow

This describes the final Slice 3 workflow. Slices 1 and 2 replace the SignalWire call with a mock call transport while keeping the same eligibility, persona, result, and write-back shape.

1. A Dynamics workflow or user creates Call Queue Item records for Accounts in the ALF campaign.
2. The queue worker polls for due items.
3. The worker checks eligibility.
4. The worker places a SignalWire outbound call.
5. The ALF persona introduces itself and discloses that it is an AI assistant calling on behalf of Medx.
6. The persona asks whether the facility is interested in learning more.
7. If appropriate, the persona verifies an existing email or asks for the best email.
8. If interest is detected, the persona asks whether tomorrow morning local time works for a callback.
9. The system writes the outcome to Dynamics.
10. The system creates a Task for a human callback when needed.
11. The queue item is finalized or scheduled for retry.

## Eligibility Rules

The system must not dial unless all required checks pass.

Required checks:

- Queue item status is `ready`.
- Campaign is active.
- Account is active.
- Phone number is present and normalized.
- Time zone is present or can be derived.
- Current time is within the configured local call window.
- Account or Contact is not marked do-not-call.
- Account or Contact has not opted out of this outreach type.
- Attempt count is below the campaign maximum.
- The queue item is not locked by another worker.

Recommended default call window:

- Monday through Friday.
- 9:00 AM to 5:00 PM target local time.
- Exclude configured holidays.

The exact policy should remain deployment-configurable.

## Persona Requirements

### Required Behavior

The persona must:

- State that it is an AI assistant calling on behalf of Medx.
- Ask for the appropriate person if a gatekeeper answers.
- Keep the conversation brief.
- Ask whether the facility is interested in learning more.
- Verify an existing email when one is present.
- Capture an email when the facility is interested and no email is available.
- Offer a callback for tomorrow morning local time when interest is present.
- End politely when the facility is not interested.
- Mark do-not-call when the recipient clearly requests no further calls.
- Escalate to human review when the conversation is ambiguous, hostile, or outside scope.

### Prohibited Behavior

The persona must not:

- Claim to be human.
- Claim to be a clinician.
- Provide medical advice.
- Ask for resident or patient health information.
- Make pricing, coverage, legal, or clinical claims unless explicitly configured.
- Promise a specific callback time unless scheduling integration can reserve it.
- Continue after a clear opt-out.

### Conversation Slots

The persona should attempt to extract:

- Person reached name, if volunteered.
- Person reached role, if volunteered.
- Interest level.
- Existing email verified: yes/no.
- Captured email.
- Preferred callback window.
- Do-not-call request.
- Wrong-number indication.
- Human-review reason.

## Disposition Definitions

### `interested_callback_requested`

The facility expressed interest and agreed to a callback window.

Required write-back:

- Phone Call activity.
- Callback Task.
- Queue item completed.
- Email update if captured or verified.

### `interested_email_captured`

The facility expressed interest and provided or verified an email, but did not agree to a callback time.

Required write-back:

- Phone Call activity.
- Follow-up Task.
- Queue item completed.
- Email update if captured or verified.

### `not_interested`

The facility clearly declined.

Required write-back:

- Phone Call activity.
- Queue item completed.
- Account note only if there is a durable reason worth preserving.

### `call_back_later`

The recipient asked for another call but did not express clear interest.

Required write-back:

- Phone Call activity.
- Queue item retry scheduled or Task created based on campaign policy.

### `wrong_number`

The number does not belong to the target facility.

Required write-back:

- Phone Call activity when connected.
- Queue item completed.
- Account flagged for phone review.

### `no_answer`

The call did not connect to a person or voicemail.

Required write-back:

- Queue attempt recorded.
- Retry scheduled if attempts remain.

### `voicemail`

The call reached voicemail.

Required write-back:

- Queue attempt recorded.
- Optional voicemail note depending on campaign policy.
- Retry scheduled if attempts remain.

### `gatekeeper_reached`

A gatekeeper answered but did not provide enough information to classify interest.

Required write-back:

- Phone Call activity.
- Retry or human-review Task based on policy.

### `do_not_call`

The recipient requested no further calls.

Required write-back:

- Phone Call activity.
- Queue item completed.
- DNC or opt-out field updated in CRM where policy allows.

### `needs_human_review`

The AI could not safely or confidently classify the outcome.

Required write-back:

- Phone Call activity.
- Human review Task with reason.
- Queue item completed or paused.

## CRM Requirements

### Source Records

The queue item should reference:

- Account.
- Optional Contact.
- Campaign.
- Phone number.
- Time zone.
- Attempt count.
- Next attempt time.

### Phone Call Activity

For connected calls, create a Phone Call activity with:

- Subject.
- Regarding Account.
- Optional Contact.
- Direction: outbound.
- Start and end time.
- Duration.
- Disposition.
- Summary.
- Transcript or transcript pointer based on retention policy.
- AI persona name and version.

### Callback Task

For interested or review-needed outcomes, create a Task with:

- Owner or queue.
- Regarding Account.
- Optional Contact.
- Due date/time.
- Local time zone.
- Phone number.
- Email if captured.
- Disposition.
- Summary.
- Human action requested.
- Transcript pointer when available.

### Account and Contact Updates

The system may update:

- Email when verified or captured.
- Phone validity flags.
- DNC or opt-out fields.
- Durable notes such as "wrong number" or "requested no further calls."

The system should not overwrite existing high-confidence CRM data with lower-confidence AI extraction.

## Reporting Requirements

The MVP should support campaign reporting through CRM fields and exported logs.

Minimum report fields:

- Queue items created.
- Calls attempted.
- Calls connected.
- Final disposition counts.
- Interested count.
- Callback tasks created.
- DNC count.
- Wrong-number count.
- Average call duration.
- Provider failure count.
- CRM write-back failure count.

## Acceptance Criteria

- Slice 1 can process a mock call against a mock CRM/write-back target.
- Slice 2 can process a mock call against a real Dynamics queue and write-back path.
- Slice 3 can produce a real outbound call through SignalWire from a Dynamics queue item.
- No call is placed when eligibility checks fail.
- A connected call produces a Phone Call activity in Dynamics.
- An interested outcome creates a callback Task.
- A DNC request prevents further automated attempts for that target.
- No-answer and voicemail outcomes follow retry policy.
- Duplicate SignalWire callbacks do not create duplicate CRM records.
- The transcript, summary, extracted fields, and disposition are tied to one session ID.
- The persona remains within non-clinical, appointment-setting scope.

## Risks

- Call recipients may react negatively to AI disclosure or automated outreach.
- Local calling, recording, consent, and DNC rules vary by region.
- CRM data may have missing time zones, invalid phone numbers, or stale contacts.
- Real-time voice latency may reduce call quality.
- Email extraction may be error-prone over audio and should be confirmed.
- The AI may classify ambiguous conversations incorrectly without human review.

## Open Questions

- What exact AI disclosure language should Medx approve?
- What should "tomorrow morning" mean: 8-11 AM, 9-12 PM, or another range?
- Who owns callback Tasks by default?
- Should voicemail messages be left, or should the AI hang up when voicemail is detected?
- Should not-interested outcomes suppress future campaigns or only this campaign?
- Should email updates require human approval before writing to Contact or Account?
- Should connected calls store full transcript, summary only, or both?
