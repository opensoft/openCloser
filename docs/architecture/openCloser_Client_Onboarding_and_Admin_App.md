# openCloser Client Onboarding and Admin App

Status: Draft

Last updated: 2026-05-25

## Purpose

This document defines how a client installs openCloser into its Microsoft
tenant, connects Dynamics 365 / Dataverse, and monitors basic system health.

The target experience is simple for a client administrator:

```text
Download or open openCloser Admin
  -> sign in with Microsoft
  -> create openCloser account
  -> grant tenant consent
  -> select CRM environment
  -> install Dynamics managed solution
  -> verify connection
  -> activate campaigns
```

Repository and release boundaries are defined in
[Release and Repository Strategy](./openCloser_Release_and_Repo_Strategy.md).

## Product Boundary

The admin app is a narrow install and operations surface. It is not the pilot
operator UI and it must not become a parallel CRM.

Allowed:

- Account setup.
- Microsoft tenant connection.
- CRM environment selection.
- Dynamics extension install guidance/status.
- openCloser runtime health.
- Active campaign overview.
- Campaign pause/resume controls.
- Dry-run/write-enabled toggles for test campaigns.
- Call, write-back, and integration error summaries.

Not allowed for the MVP call-loop:

- Full campaign builder.
- Custom task queue.
- Transcript review console.
- Analytics dashboard.
- Replacement CRM screens for operators.
- Editing CRM business records outside the approved setup/configuration scope.

Operators still work in Dynamics. The admin app exists so customer admins can
install, configure, verify, and monitor openCloser without reading developer
docs.

## Deployment Components

### openCloser Admin

A small Flutter admin app, mobile-first and responsive enough for tablet and web
from the start. The same codebase should support mobile packaging and a hosted
web/admin build unless a later release decision proves separate clients are
needed.

Responsibilities:

- Microsoft sign-in.
- Tenant and environment discovery.
- Customer account creation.
- Install checklist and progress.
- Health checks for API, Dataverse access, telephony, model runtime, and CRM
  write-back.
- Read-only campaign status and small administrative controls.

Admin consent, Power Platform redirects, and failed-install troubleshooting are
often browser-oriented, so the first Flutter build should support web and mobile
layouts rather than mobile-only screens.

## Independent Flutter Feature Slices

The Flutter admin app can advance independently from the Python runtime as long
as it works against generated clients, fixture data, and the versioned Admin API
contract.

| Feature | Scope | Backend Dependency |
|---|---|---|
| Admin app scaffold | Flutter project, routing, theme, responsive layout, auth/loading/error states. | None; local fixtures only. |
| Runtime API client and mocks | Generated or hand-wrapped `/v1/admin/*` Dart client plus mock adapters. | OpenAPI draft contract only. |
| Microsoft sign-in and account setup | Sign-in entry, create/join account flow, mocked account and tenant state. | Mocked initially; real Entra flow later. |
| Tenant consent flow | Grant admin consent UI, browser/deep-link handling, pending/success/failure states. | Mocked consent endpoints initially. |
| CRM environment selection | Dataverse environment list, selected CRM, permission/availability state. | `/v1/admin/tenants/{tenant_id}/environments` when live. |
| Install verification checklist | Solution version, environment variables, Dataverse access, trigger reachability, dry-run smoke status. | `/v1/admin/crm/environments/{environment_id}/verify` when live. |
| System health dashboard | Account, tenant consent, CRM extension, Dataverse, runtime API, telephony, AI runtime, write-back. | `/v1/admin/health` when live. |
| Campaign status and controls | Active campaigns, eligible leads, attempted calls, failures, pause/resume. | `/v1/admin/campaigns` and pause/resume endpoints when live. |

The corresponding Python runtime work is separate. Fixture-backed Admin API
endpoints and real Dataverse-backed Admin API endpoints are `py-bench` features,
not hidden Flutter tasks.

### Dynamics Managed Solution

The Dynamics extension is installed as a managed solution for customer
environments. Source lives under:

```text
integrations/dynamics365/
```

The solution should include:

- Lead command bar button: `AI Call Lead`.
- Campaign command bar button: `Run openCloser Campaign`.
- Dataverse environment variables for openCloser endpoint and trigger mode.
- Optional Power Automate trigger flow or custom connector.
- Security role for least-privilege runtime access.
- Web resources needed by the command buttons.

The CRM extension should only collect context and trigger openCloser. It must
not implement eligibility, persona, call execution, or write-back logic.

### openCloser Cloud Runtime

The runtime owns:

- Tenant/account binding.
- CRM metadata verification.
- Eligibility and DNC rules.
- Mock or real call execution.
- Persona execution.
- Idempotent Dataverse write-back.
- Runtime logs, metrics, and health checks.

## Install Channels

### Production Channel: Microsoft AppSource

The production client path should be AppSource / Power Platform admin center.
Clients install `openCloser for Dynamics 365` as a managed solution into the
target environment.

Microsoft references:

- Dynamics app install/admin flow:
  <https://learn.microsoft.com/en-us/power-platform/admin/manage-apps>
- AppSource publishing overview:
  <https://learn.microsoft.com/en-us/power-platform/developer/appsource/publish-app>
- AppSource package requirements:
  <https://learn.microsoft.com/en-us/power-platform/developer/appsource/create-package-app>

### Preview Channel: Managed Solution Zip

Before AppSource approval, provide a signed managed solution zip from openCloser
release artifacts. This is acceptable for pilots, but the admin app must make
the trust boundary clear:

- The client imports a managed solution from openCloser.
- The client admin must have sufficient Power Platform/Dynamics permissions.
- Updates are handled by importing newer managed solution versions.

## Client Install Flow

### 1. Sign In and Create Account

The admin opens openCloser Admin and signs in with Microsoft. The app creates or
joins an openCloser account and records:

- Tenant ID.
- Admin user ID.
- Organization name.
- Selected subscription/plan.

### 2. Grant Tenant Consent

The admin grants consent to the openCloser multi-tenant Entra app. The consent
screen must be explicit about the permissions requested.

Microsoft reference:

- Admin consent endpoint:
  <https://learn.microsoft.com/en-us/entra/identity-platform/v2-admin-consent>

The app must validate the returned state and tenant through normal auth/token
validation. It must not trust URL parameters alone.

### 3. Select CRM Environment

The admin chooses the Dataverse environment that contains Dynamics/Sales data.
The admin app verifies:

- Environment URL.
- Dataverse database is available.
- Dynamics/Sales tables required for the selected install path are available.
- Current admin has enough permission to install or configure the solution.

### 4. Install Dynamics Extension

Production path:

- Admin clicks the AppSource/Power Platform install link.
- Power Platform admin center installs the managed solution into the selected
  environment.
- Admin app polls or asks the runtime to verify solution presence/version.

Preview path:

- Admin downloads the managed solution zip from openCloser.
- Admin imports it into the target environment.
- Admin returns to openCloser Admin for verification.

### 5. Configure Environment Variables

The managed solution carries Dataverse environment variables. The admin app
should guide or automate setting:

- `oc_OpenCloserApiBaseUrl`.
- `oc_OpenCloserTriggerMode`.
- `oc_OpenCloserPowerAutomateTriggerUrl`, if using Power Automate.
- `oc_OpenCloserDefaultRunMode`.
- `oc_OpenCloserTestModeEnabled`.
- `oc_OpenCloserMaxCampaignBatchSize`.
- `oc_OpenCloserAllowedCampaignCodes`.

For detailed variable definitions, see:

```text
integrations/dynamics365/docs/configuration.md
```

### 6. Create Integration Identity

The runtime needs a Dataverse access path with least privilege. Use a service
principal/application user for server-side access where possible.

Microsoft references:

- Service principal Dataverse connector pattern:
  <https://learn.microsoft.com/en-us/power-automate/dataverse/manage-dataverse-connections>
- Power Platform environment app access and application users:
  <https://learn.microsoft.com/en-us/power-platform/admin/control-app-access-environment>

The openCloser security role should grant only the table and operation access
needed for the selected deployment:

- Read campaign and lead/queue records.
- Create Phone Call activities.
- Create Tasks.
- Update approved queue/status/result fields.
- Read metadata required for verification.

### 7. Verify Installation

The admin app runs a verification checklist:

- Tenant consent valid.
- openCloser account active.
- Runtime reachable.
- CRM environment reachable.
- Managed solution installed and expected version present.
- Environment variables present.
- Integration identity can read required metadata.
- Lead button trigger reaches openCloser.
- Campaign button trigger reaches openCloser.
- Dry-run smoke test completes with zero CRM writes.
- Optional write-enabled test lead creates the expected Phone Call/Task/status
  records.

### 8. Activate Campaigns

After verification, the admin enables the target campaign. Dynamics remains the
surface for campaign records, leads, Phone Call activities, Tasks, and human
follow-up.

The admin app may show campaign-level status:

- Active or paused.
- Eligible leads.
- Calls attempted today.
- Connected calls.
- Dispositions.
- Failed writes.
- Items needing human review.

## Admin App Status Model

The admin app should show a compact status page:

| Area | Status examples |
|---|---|
| Account | Active, billing pending, suspended |
| Tenant consent | Missing, granted, expired/revoked |
| CRM extension | Not installed, installed, update available |
| Dataverse access | Connected, permission gap, metadata drift |
| Runtime API | Healthy, degraded, unavailable |
| Telephony | Not configured, ready, provider error |
| AI runtime | Not configured, ready, provider error |
| Campaigns | Active, paused, blocked, test mode |
| Write-back | Healthy, retrying, failed |

## Runtime APIs Needed by Admin App

Initial admin endpoints:

```text
POST /v1/admin/accounts
GET /v1/admin/account
POST /v1/admin/microsoft/consent/start
POST /v1/admin/microsoft/consent/complete
GET /v1/admin/tenants/{tenant_id}/environments
GET /v1/admin/crm/environments/{environment_id}/status
POST /v1/admin/crm/environments/{environment_id}/verify
GET /v1/admin/crm/environments/{environment_id}/solution
GET /v1/admin/campaigns
POST /v1/admin/campaigns/{campaign_id}/pause
POST /v1/admin/campaigns/{campaign_id}/resume
GET /v1/admin/health
```

These endpoints are separate from the CRM-trigger endpoints:

```text
POST /v1/crm/dataverse/leads/{lead_id}/ai-call
POST /v1/crm/dataverse/campaigns/{campaign_id}/run
```

The admin app should live in this repository only while it is a scaffold or
contract design artifact. If it starts here, the temporary source root should be
`apps/admin_flutter/`. Before external client release, it should move to
`openCloser-admin` so web/mobile packaging and runtime deployments can release
on separate schedules.

## Release Phases

### Phase A: Flutter Scaffold and Mock Admin

- Flutter project shell.
- Generated or wrapped Admin API client from the OpenAPI contract.
- Mock adapters for account, consent, environments, verification, health, and
  campaigns.
- Demoable install/status flows without live CRM or live auth.

### Phase B: Pilot Installer

- Managed solution zip from release artifacts.
- Manual import with guided checklist.
- Admin app shows install status and health.
- Dry-run smoke test supported.

### Phase C: AppSource Install

- AppSource listing and package.
- Admin app deep-links to install/manage flow.
- Solution version detection.
- Guided update path.

### Phase D: Admin App Controls

- Active campaigns overview.
- Pause/resume.
- Batch limit/test mode controls.
- Failed integration and write-back triage.

### Phase E: Native Mobile Packaging

- Native app-store distribution if needed.
- Push notifications for degraded integrations and campaign failures.
- Same backend and status model as responsive admin web.

## Open Questions

- Which Flutter release target ships first for pilots: hosted web, sideloaded
  mobile build, or app-store/TestFlight distribution?
- Will AppSource be required before first external pilot, or is a managed zip
  acceptable for design partners?
- Which Entra permissions are the minimum viable set for tenant discovery and
  install verification?
- Should the customer create the service principal, or should openCloser provide
  a multi-tenant app plus documented Dataverse application-user setup?
- How much solution configuration can the admin app automate versus guiding the
  admin through Power Platform admin center?
