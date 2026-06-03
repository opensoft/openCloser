# Feature 009 Speckit Specify Prompt

Run from the root checkout while on `main`. OpenSpec/Speckit shell commands
should run from `py-bench`; the root checkout there is
`/workspace/projects/openCloser`.

```text
GIT_BRANCH_NAME=009-runtime-admin-api-fixtures SPECIFY_FEATURE_DIRECTORY=specs/009-runtime-admin-api-fixtures /speckit.specify Create Feature 009: Runtime Admin API Fixtures.

Generate the Speckit feature specification for openCloser Feature 009. This Python runtime feature implements fixture-backed `/v1/admin/*` endpoints and contract tests matching `contracts/opencloser-runtime-v1.openapi.yaml`, so the Flutter admin app can move from in-app mocks to a local runtime fixture server.

Authoritative context:
- `.specify/memory/constitution.md`
- `specs/README.md`
- `docs/architecture/openCloser_Client_Onboarding_and_Admin_App.md`
- `docs/architecture/openCloser_Release_and_Repo_Strategy.md`
- `docs/architecture/openCloser_Architecture.md`
- `docs/prds/openCloser_MVP.md`
- `docs/prds/openCloser_PRD.md`
- `contracts/opencloser-runtime-v1.openapi.yaml`
- `specs/005-admin-openapi-client-mocks/speckit-specify-prompt.md`
- `specs/008-admin-health-campaign-status/speckit-specify-prompt.md`

Feature 009 target slice:
- Bench owner: `py-bench`.
- Target phase: Python runtime fixture-backed Admin API.
- Goal: provide local FastAPI-compatible Admin API endpoints that satisfy the draft OpenAPI contract using deterministic fixtures, with no live Microsoft, Dataverse, SignalWire, or model-provider dependencies.
- The smallest independently demonstrable outcome is: a local runtime process can return valid fixture responses for every `/v1/admin/*` operation, and contract tests verify response shape and key error paths.
- This feature must be fully owned by `py-bench`. Do not add Flutter UI tasks, Dart generated client changes, or real Dataverse/Entra integrations.

Admin endpoints in scope:
- `POST /v1/admin/accounts`
- `GET /v1/admin/account`
- `POST /v1/admin/microsoft/consent/start`
- `POST /v1/admin/microsoft/consent/complete`
- `GET /v1/admin/tenants/{tenant_id}/environments`
- `GET /v1/admin/crm/environments/{environment_id}/status`
- `POST /v1/admin/crm/environments/{environment_id}/verify`
- `GET /v1/admin/crm/environments/{environment_id}/solution`
- `GET /v1/admin/campaigns`
- `POST /v1/admin/campaigns/{campaign_id}/pause`
- `POST /v1/admin/campaigns/{campaign_id}/resume`
- `GET /v1/admin/health`

Required scope:
- Implement fixture-backed handlers or service methods for each Admin API operation.
- Keep fixture state deterministic and local, suitable for Flutter integration tests and demos.
- Provide fixture scenarios for active, billing pending, suspended, missing/granted/revoked consent, connected/permission-gap/unavailable Dataverse, installed/not-installed/update-available solution, passing/failing verification, empty campaign list, active/paused/blocked/test-mode campaigns, healthy/degraded/unavailable runtime.
- Implement user-safe `Problem` errors with `message`, optional `code`, and optional `correlationId`.
- Add contract tests that validate success response shapes against the OpenAPI draft or equivalent schema assertions.
- Add negative tests for invalid tenant/environment/campaign identifiers and unsupported fixture states.
- Document local startup and fixture selection for Flutter consumers.

User stories the generated spec should cover:
- A Flutter developer can point the admin app at a local runtime and receive Admin API fixture responses.
- A backend developer can run contract tests proving every Admin API fixture response matches the draft contract.
- A tester can switch fixture scenarios to reproduce healthy, pending, failing, and unavailable admin states.
- Invalid or unknown IDs return user-safe errors rather than stack traces.

Out of scope for Feature 009:
- Real Microsoft sign-in or tenant consent validation.
- Real Dataverse environment discovery, solution detection, verification, or campaign status.
- Real pause/resume effects on runtime workers or CRM.
- Flutter UI implementation or Dart client regeneration.
- Feature 003 SignalWire/Pipecat real-call work.

Expected measurable outcomes:
- Every `/v1/admin/*` endpoint in the draft contract has a fixture-backed runtime implementation.
- Contract tests cover every endpoint success response.
- Error tests cover representative bad input and unavailable fixture states.
- A documented local command starts the fixture-backed API for Flutter integration.

Specification instructions:
- Write the spec as requirements, not an implementation plan.
- Include the required Bench Owner field with `py-bench`.
- State clearly that this is a fixture server and must not pretend to verify real tenant, CRM, telephony, or model health.
- Preserve CRM-first boundaries: no operator UI, no CRM replacement, and no business-record editing.
```
