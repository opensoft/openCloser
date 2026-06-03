# openCloser Release and Repository Strategy

Status: Draft

Last updated: 2026-05-25

## Decision

Keep the Dynamics and admin-app scaffolds in the core `openCloser` repository
until the Feature 002/003 runtime contracts stabilize. Split installable client
surfaces into separate repositories before the first external client release.

Target repositories:

```text
openCloser                # core runtime, API, worker, personas, CRM adapter
openCloser-dynamics365    # managed solution, command buttons, AppSource package
openCloser-admin          # Flutter responsive/mobile admin app
```

## Why Not Split Immediately

The trigger APIs, install flow, Dataverse mapping, and CRM write-back behavior
are still being defined with the runtime. Keeping the scaffold in one repository
for now reduces drift while the thin MVP proves:

- Feature 002: mock call, real CRM.
- Feature 003: real call, real CRM.
- Dynamics command buttons.
- Flutter Admin install/status flow.

## Why Split Before Client Release

Each component has a different release cadence and review process.

| Component | Release driver | Reason to split |
|---|---|---|
| `openCloser` | Runtime/API/worker deploys | Backend fixes and call behavior should deploy without mobile or AppSource release gates. |
| `openCloser-dynamics365` | Managed solution/AppSource | CRM solution versioning, AppSource packaging, and customer imports need independent lifecycle. |
| `openCloser-admin` | Flutter web/mobile admin app | Auth redirects, mobile/web builds, app-store packaging, and UI releases should not be tied to runtime commits. |

Feature numbering and bench ownership are tracked in
[`specs/README.md`](../../specs/README.md). Feature 003 is reserved for
`py-bench` runtime work only. Flutter admin app work starts at Feature 004+ and
is planned as `flutterBench` work so it can proceed while Python runtime work
continues.

## Stable Contracts

Cross-repo communication must use versioned APIs. Version `v1` is the first
public contract surface.

Canonical draft contract:

```text
contracts/opencloser-runtime-v1.openapi.yaml
```

### Dynamics Solution to Runtime

```text
POST /v1/crm/dataverse/leads/{lead_id}/ai-call
POST /v1/crm/dataverse/campaigns/{campaign_id}/run
```

### Admin App to Runtime

```text
POST /v1/admin/accounts
GET  /v1/admin/account
POST /v1/admin/microsoft/consent/start
POST /v1/admin/microsoft/consent/complete
GET  /v1/admin/tenants/{tenant_id}/environments
GET  /v1/admin/crm/environments/{environment_id}/status
POST /v1/admin/crm/environments/{environment_id}/verify
GET  /v1/admin/crm/environments/{environment_id}/solution
GET  /v1/admin/campaigns
POST /v1/admin/campaigns/{campaign_id}/pause
POST /v1/admin/campaigns/{campaign_id}/resume
GET  /v1/admin/health
```

### Runtime to Dataverse

The runtime uses the Dataverse Web API directly. The Dynamics managed solution
must not call runtime internals or rely on unversioned backend routes.

## Compatibility Matrix

Maintain a compatibility table in release notes for each repo.

Initial target:

| Component | Version | Compatible with |
|---|---|---|
| openCloser runtime | `0.x` | API `v1` during MVP stabilization |
| openCloser Dynamics solution | `0.x` | Runtime API `v1` |
| openCloser Admin | `0.x` | Runtime Admin API `v1` |

Before external client release, replace `0.x` with concrete semver versions and
state the supported minimum runtime version.

## Split Criteria

Create `openCloser-admin` when at least one of these is true:

- The admin app has a real build pipeline or deployment target.
- It needs auth redirect configuration independent of runtime deploys.
- It needs customer-facing releases or mobile packaging.
- Flutter app-store, web-hosting, or release-signing concerns start to drive
  changes independently of runtime work.

Create `openCloser-dynamics365` when at least one of these is true:

- The managed solution can be packed from source.
- AppSource submission starts.
- A customer imports a managed solution zip.
- CRM solution versioning needs to move independently from backend deploys.

## Migration Plan

1. Keep source scaffold under `integrations/dynamics365/` and admin docs under
   `docs/architecture/` while Feature 002/003 contracts settle. If the Flutter
   app starts before the repo split, use `apps/admin_flutter/` as the temporary
   subtree root.
2. Require all CRM/admin routes to use `/v1`.
3. Add contract tests in `openCloser` for `/v1` request/response payloads.
4. When split criteria are met, create the target repo.
5. Move the relevant directory history with `git subtree split` or an
   equivalent history-preserving export.
6. Add the source repo as read-only reference in this repo's docs.
7. Keep shared API contracts duplicated as generated artifacts or pulled from a
   release tag, not hand-edited independently.

Example split commands for the Dynamics extension:

```bash
git subtree split --prefix=integrations/dynamics365 -b split/dynamics365
```

Example split commands for a future admin app if it starts under
`apps/admin_flutter`:

```bash
git subtree split --prefix=apps/admin_flutter -b split/admin
```

## Repository Ownership

`openCloser` remains authoritative for:

- Interaction runtime.
- Persona behavior.
- Eligibility and DNC rules.
- CRM write-back semantics.
- API contracts.
- Test fixtures that prove the call loop.

`openCloser-dynamics365` becomes authoritative for:

- Command bar buttons.
- Web resources.
- Power Automate trigger flow.
- Managed solution source.
- AppSource package metadata.
- Dynamics install instructions.

`openCloser-admin` becomes authoritative for:

- Admin sign-in and onboarding UX.
- Tenant/environment selection UX.
- Install verification UX.
- Health and campaign status screens.
- Mobile/web packaging.

## Guardrails

- Do not move eligibility, DNC, persona, call execution, or write-back logic into
  the Dynamics solution or admin app.
- Do not add unversioned trigger routes once `/v1` exists.
- Do not let the admin app become a campaign builder or CRM replacement for the
  MVP.
- Do not require a mobile/AppSource release for routine runtime fixes.
