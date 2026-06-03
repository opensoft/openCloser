# openCloser Trigger API Contract

The Dynamics extension triggers openCloser through one of two modes:

- `direct-api`: command bar JavaScript posts directly to the openCloser API.
- `power-automate`: command bar JavaScript posts to a configured Power Automate
  trigger URL, and the flow calls openCloser server-side.

`power-automate` is preferred for customer installs when browser-to-openCloser
auth, CORS, or network routing is not yet standardized.

Canonical draft OpenAPI contract:

```text
../../../contracts/opencloser-runtime-v1.openapi.yaml
```

## Endpoints

The openCloser runtime should expose these endpoints when Feature 002 is wired
for CRM triggers:

```text
POST /v1/crm/dataverse/leads/{lead_id}/ai-call
POST /v1/crm/dataverse/campaigns/{campaign_id}/run
```

The campaign endpoint may process multiple eligible Leads, but the runtime should
still execute one Lead attempt at a time internally and respect the configured
batch limit.

## Request Body

```json
{
  "source": "dynamics365-command-bar",
  "action": "ai_call_lead",
  "record": {
    "entityName": "lead",
    "id": "00000000-0000-0000-0000-000000000000"
  },
  "crm": {
    "clientUrl": "https://org.crm.dynamics.com",
    "organizationId": "00000000-0000-0000-0000-000000000000",
    "userId": "00000000-0000-0000-0000-000000000000"
  },
  "run": {
    "mode": "dry_run",
    "testMode": false,
    "maxCampaignBatchSize": 10,
    "assignmentTag": null,
    "requestedAt": "2026-05-24T00:00:00.000Z"
  }
}
```

For the campaign button, `action` is `run_campaign`, `record.entityName` is
`campaign`, and `record.id` is the Campaign GUID.

## Response Body

The command bar handler expects JSON. The exact runtime shape can grow, but the
first version should return:

```json
{
  "status": "accepted",
  "message": "openCloser run accepted.",
  "runId": "optional-runtime-run-id"
}
```

Non-2xx responses should include a short `message` field that is safe to show to
the CRM user.
