# openCloser Tester Campaign Mock Calls

This directory defines 30 deterministic mock-call assignments for the live CRM
test campaign `OPEN-CLOSER-TESTER`.

Use `mock_calls_catalog.json` as the source of truth. `lead_call_matrix.csv` is a
flat operator-friendly view of the same assignments.

## Tagging Contract

Every assignment has these stable identifiers:

- `campaign_code`: `OPEN-CLOSER-TESTER`
- `lead_test_id`: the test Lead marker stored in CRM as `cr487_facilityid`
- `crm_lead_id`: the Dataverse Lead GUID verified on 2026-05-24
- `mock_call_id`: one of `OC-MOCKCALL-001` through `OC-MOCKCALL-030`
- `mock_provider_call_id`: deterministic mock transport call identifier
- `assignment_tag`: `{campaign_code}::{lead_test_id}::{mock_call_id}`

Use `assignment_tag` as the join key across local artifacts, CRM Phone Call
activity text, CRM Task text, and any test harness logs. Do not treat it as a
production idempotency key unless Feature 002 maps a real metadata-verified
Dataverse field for that purpose.

Suggested CRM-visible tags:

- Phone Call subject prefix: `[TEST][OPEN-CLOSER-TESTER][OC-MOCKCALL-###]`
- Phone Call or Task description line:
  `assignment_tag=OPEN-CLOSER-TESTER::OC-TEST-###::OC-MOCKCALL-###`
- Local artifact metadata fields: `campaign_code`, `lead_test_id`,
  `mock_call_id`, `mock_provider_call_id`, `assignment_tag`

## Usage

Feature 002 processes one queue item per invocation. Pick one row from the CSV
or one `mock_calls` entry from the catalog, then run the Slice 2 command against
that one CRM record.

When the Dataverse queue source is the standard Lead table, use `crm_lead_id` as
the queue-item selector. If a later queue table is introduced, create or select
the queue row bound to the same Lead and copy `lead_test_id`, `mock_call_id`, and
`assignment_tag` into the run metadata.

Rows whose `dominant_path` is `eligibility` are expected to block before call
placement. Their fixture paths are retained so the assignment matrix stays
complete, but the transport and conversation fixtures should not be consumed.

