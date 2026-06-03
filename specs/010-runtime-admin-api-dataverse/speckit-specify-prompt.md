# Feature 010 Speckit Specify Prompt

Run from the root checkout while on `main`. OpenSpec/Speckit shell commands
should run from `py-bench`; the root checkout there is
`/workspace/projects/openCloser`.

```text
GIT_BRANCH_NAME=010-runtime-admin-api-dataverse SPECIFY_FEATURE_DIRECTORY=specs/010-runtime-admin-api-dataverse /speckit.specify Create Feature 010: Runtime Admin API Dataverse Integration.

Generate the Speckit feature specification for openCloser Feature 010. This Python runtime feature replaces or supplements fixture-backed Admin API responses with real account, tenant consent, Dataverse environment, managed solution, verification, health, and campaign status integrations while preserving the same `/v1/admin/*` contract.

Authoritative context:
- `.specify/memory/constitution.md`
- `specs/README.md`
- `docs/architecture/openCloser_Client_Onboarding_and_Admin_App.md`
- `docs/architecture/openCloser_Release_and_Repo_Strategy.md`
- `docs/architecture/openCloser_Architecture.md`
- `docs/prds/openCloser_MVP.md`
- `docs/prds/openCloser_PRD.md`
- `contracts/opencloser-runtime-v1.openapi.yaml`
- `integrations/dynamics365/README.md`
- `integrations/dynamics365/docs/configuration.md`
- `integrations/dynamics365/docs/install.md`
- `specs/009-runtime-admin-api-fixtures/speckit-specify-prompt.md`
- `specs/002-mock-call-real-crm/spec.md`
- `specs/002-mock-call-real-crm/contracts/*.md`

Feature 010 target slice:
- Bench owner: `py-bench`.
- Target phase: real runtime Admin API integration.
- Goal: connect the Admin API to real configuration, tenant/account state, Microsoft consent status, Dataverse environment metadata, managed solution status, verification checks, runtime health, and campaign status while keeping the Admin API contract stable.
- The smallest independently demonstrable outcome is: against a configured test tenant/environment, the runtime can report environment access, solution/version status, verification checklist results, health, and campaign summaries through `/v1/admin/*` endpoints without changing the Flutter app contract.
- This feature must be fully owned by `py-bench`. Do not add Flutter UI tasks, Dart client changes, or Dynamics managed-solution packaging tasks.

Required scope:
- Preserve all Feature 009 endpoint paths and response shapes.
- Add real account/tenant lookup or configuration-backed account binding.
- Add real tenant consent status checks or a verified consent-state source.
- Add Dataverse environment discovery or configured environment lookup.
- Add managed solution presence/version detection.
- Add verification checks for Dataverse access, required metadata, required solution environment variables, Lead trigger reachability, Campaign trigger reachability, dry-run smoke readiness, and optional write-enabled test readiness.
- Add health aggregation for account, tenant consent, CRM extension, Dataverse access, runtime API, telephony, AI runtime, and write-back status.
- Add campaign status summaries from real CRM/runtime state for active, paused, blocked, and test-mode campaigns.
- Add pause/resume endpoint behavior only for approved campaign automation state; do not edit arbitrary CRM business records.
- Preserve fixture mode for local demos and tests if useful.
- Add integration/contract tests with mocked Dataverse/Microsoft clients and at least one documented live-test path gated by environment variables.

User stories the generated spec should cover:
- A client admin can see real CRM environment and managed solution status through the Admin API.
- A client admin can run verification and see actionable passing/failing/warning checks.
- A client admin can see real health status for runtime, CRM, telephony, AI runtime, and write-back readiness.
- A client admin can see real campaign summaries and pause/resume approved automation state.
- A backend operator can run the same endpoints in fixture mode for local demos.

Out of scope for Feature 010:
- Flutter UI or generated Dart client changes.
- AppSource submission or managed solution packaging.
- Broad campaign builder, CRM record editing, transcript console, analytics dashboard, or operator task queue.
- Feature 003 call execution behavior unless health checks need to read its configuration/state.
- Multi-CRM support.

Expected measurable outcomes:
- Every `/v1/admin/*` endpoint remains contract-compatible with the OpenAPI draft.
- Verification identifies missing solution, missing environment variables, permission gaps, metadata drift, and unavailable Dataverse states.
- Health aggregation returns user-safe degraded/unavailable states without exposing secrets.
- Pause/resume changes only approved automation state and is idempotent.
- Tests cover contract shape, mocked integration success, permission gap, missing solution, failing verification, and pause/resume idempotency.

Specification instructions:
- Write the spec as requirements, not an implementation plan.
- Include the required Bench Owner field with `py-bench`.
- State that the Flutter app consumes this through the existing Admin API and should not need contract-breaking changes.
- Require secrets to come from environment variables or a secret manager and never from tracked files.
- Require live Dataverse metadata verification before write-enabled setup or campaign-control actions.
```
