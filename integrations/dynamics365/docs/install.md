# Dynamics Install Plan

This integration is intended to ship as a Dynamics 365 managed solution.

The product-level onboarding flow is defined in:

```text
docs/architecture/openCloser_Client_Onboarding_and_Admin_App.md
```

This file is the Dynamics-specific install checklist used by that flow.

## Prerequisites

- Power Platform CLI (`pac`)
- Maker/admin access to the target Dataverse environment
- openCloser runtime endpoint reachable from the chosen trigger path
- A Dataverse security role policy that allows the user to run the command and
  allows the runtime integration identity to read/write the required CRM records

## Client Install Path

Production path:

1. Client admin opens openCloser Admin and signs in with Microsoft.
2. Admin creates or joins the openCloser account.
3. Admin grants Microsoft tenant consent.
4. Admin selects the target Dynamics/Dataverse environment.
5. Admin installs `openCloser for Dynamics 365` from AppSource / Power Platform
   admin center.
6. openCloser Admin verifies solution version, environment variables, command
   buttons, Dataverse access, and write-back readiness.
7. Admin runs dry-run smoke test.
8. Admin activates one campaign.

Preview path:

1. Client admin follows steps 1-4 above.
2. Admin downloads the managed solution zip from an openCloser release.
3. Admin imports the managed solution into the selected environment.
4. openCloser Admin verifies the same install and runtime checks.

The managed solution install is the CRM extension install. The admin app guides
and verifies it; it does not replace Power Platform's solution install and
permission model.

## Build Source Solution

Initialize the solution source once:

```bash
cd integrations/dynamics365/solution/src
pac solution init --publisher-name openCloser --publisher-prefix oc
```

Then add these solution components through maker tooling or PAC-backed export:

- Environment variables from [configuration.md](configuration.md)
- Lead command bar button that calls
  `OpenCloser.Commands.aiCallLead` with `PrimaryControl`
- Campaign command bar button that calls
  `OpenCloser.Commands.runCampaign` with `PrimaryControl`
- JavaScript web resource from
  `integrations/dynamics365/webresources/opencloser_command.js`
- Optional Power Automate flow from `flows/opencloser-trigger-flow`

Export/unpack back into `solution/src` after each maker-side change so the
solution source remains reviewable.

## Pack

```bash
integrations/dynamics365/scripts/pack-solution.sh Managed
```

The managed zip is written to:

```text
integrations/dynamics365/solution/managed/
```

## Configure Deployment Settings

Create a local settings file:

```bash
OPENCLOSER_API_BASE_URL="https://opencloser.example.com" \
OPENCLOSER_TRIGGER_MODE="direct-api" \
integrations/dynamics365/scripts/configure-environment.sh
```

The local settings file is gitignored.

## Import

Authenticate with PAC, then import:

```bash
pac auth create --url https://<org>.crm.dynamics.com
integrations/dynamics365/scripts/import-solution.sh \
  integrations/dynamics365/solution/managed/openCloser.Dynamics365.managed.zip \
  integrations/dynamics365/solution/deployment-settings.local.json
```

## Manual Smoke Test

1. Open a test Lead in the openCloser tester campaign.
2. Click `AI Call Lead`.
3. Confirm openCloser receives the request.
4. Verify the run writes or plans the expected Phone Call, Task, and status data.
5. Open the test Campaign.
6. Click `Run openCloser Campaign`.
7. Confirm the campaign trigger respects the configured batch limit.

## Admin App Verification Checklist

After install, openCloser Admin should report:

- Tenant consent granted.
- Account active.
- Runtime API reachable.
- Dynamics managed solution installed.
- Expected solution version present.
- Environment variables configured.
- Dataverse metadata verification passes.
- Integration identity has required privileges.
- Lead button trigger accepted.
- Campaign button trigger accepted.
- Dry-run produces planned write-back artifacts with zero CRM writes.
- Optional write-enabled test creates the expected Phone Call/Task/status
  records.
