# Dynamics Configuration

The managed solution should define these Dataverse environment variables.

| Schema name | Required | Default | Purpose |
|---|---:|---|---|
| `oc_OpenCloserApiBaseUrl` | yes for `direct-api` | none | Base URL for the openCloser runtime API. |
| `oc_OpenCloserTriggerMode` | yes | `direct-api` | Trigger mode: `direct-api` or `power-automate`. |
| `oc_OpenCloserPowerAutomateTriggerUrl` | yes for `power-automate` | none | HTTP trigger URL for the openCloser trigger flow. Treat as secret. |
| `oc_OpenCloserDefaultRunMode` | yes | `dry_run` | Runtime mode passed to openCloser: `dry_run` or `write`. |
| `oc_OpenCloserTestModeEnabled` | yes | `false` | Enables test metadata in calls where supported. |
| `oc_OpenCloserMaxCampaignBatchSize` | yes | `10` | Max Leads a campaign trigger should request per run. |
| `oc_OpenCloserAllowedCampaignCodes` | no | blank | Optional comma-separated allowlist of campaign codes. |

## Runtime Boundary

These variables only control how CRM triggers openCloser. They do not replace
openCloser runtime configuration, Dataverse metadata verification, eligibility,
DNC handling, attempt limits, or write-back idempotency.

## Test Campaign Metadata

For the repo test campaign, the fixture catalog lives at:

```text
tests/fixtures/opencloser_tester_campaign/mock_calls_catalog.json
```

The CRM command layer should pass `assignmentTag` only when a test harness or
operator explicitly selects a mock-call assignment. Normal production CRM button
clicks should leave `assignmentTag` null.

