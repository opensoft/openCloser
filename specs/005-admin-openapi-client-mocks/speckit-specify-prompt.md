# Feature 005 Speckit Specify Prompt

Run from the root checkout while on `main`. OpenSpec/Speckit shell commands
should run from `py-bench`; the root checkout there is
`/workspace/projects/openCloser`. This feature is owned by `flutterBench` for
implementation after the spec is created.

```text
GIT_BRANCH_NAME=005-admin-openapi-client-mocks SPECIFY_FEATURE_DIRECTORY=specs/005-admin-openapi-client-mocks /speckit.specify Create Feature 005: Admin OpenAPI Client and Mocks.

Generate the Speckit feature specification for openCloser Feature 005. This feature adds the Flutter admin app's typed Runtime Admin API client and mock data layer from the draft OpenAPI contract, without requiring live Python endpoints.

Authoritative context:
- `.specify/memory/constitution.md`
- `specs/README.md`
- `docs/architecture/openCloser_Client_Onboarding_and_Admin_App.md`
- `docs/architecture/openCloser_Release_and_Repo_Strategy.md`
- `docs/prds/openCloser_MVP.md`
- `docs/prds/openCloser_PRD.md`
- `contracts/opencloser-runtime-v1.openapi.yaml`
- `specs/004-admin-flutter-scaffold/speckit-specify-prompt.md`

Feature 005 target slice:
- Bench owner: `flutterBench`.
- Target phase: Flutter admin client/data foundation.
- Goal: give the Flutter admin app a typed, swappable API boundary for all draft `/v1/admin/*` endpoints and a deterministic mock adapter that supports continued UI development.
- The smallest independently demonstrable outcome is: Flutter screens or tests can request account, consent, environments, CRM status, solution, verification, campaigns, pause/resume, and health data through one client interface and receive deterministic mock responses.
- This feature must be fully owned by `flutterBench`. Do not implement FastAPI routes, Dataverse calls, or real Entra consent.

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

Contract objects in scope:
- `CreateAccountRequest`, `AccountResponse`
- `ConsentStartRequest`, `ConsentStartResponse`
- `ConsentCompleteRequest`, `TenantConsentStatus`
- `CrmEnvironment`, `CrmEnvironmentStatus`, `SolutionStatus`
- `VerificationReport`, `VerificationCheck`
- `CampaignSummary`, `AdminHealth`
- `Problem`

Required scope:
- Generate or hand-wrap Dart models and client methods for the Admin API draft.
- Provide a transport abstraction that can swap between mock adapter and real HTTP adapter later.
- Provide deterministic mock adapters for success, pending, warning, failure, empty-list, permission-gap, and unavailable states.
- Normalize user-safe error handling using the `Problem` shape and correlation IDs when present.
- Keep mock data separate from UI widgets so Feature 006-008 screens can use the same interface.
- Add tests proving mock adapter coverage for every `/v1/admin/*` method.
- Document how the client is regenerated or manually updated when `contracts/opencloser-runtime-v1.openapi.yaml` changes.

User stories the generated spec should cover:
- A Flutter screen can load admin account state through a typed client without knowing whether the data is mocked or real.
- A Flutter screen can exercise tenant consent, environment, verification, health, and campaign states through deterministic mocks.
- A developer can force success, failure, pending, permission-gap, unavailable, and empty states for UI testing.
- API errors are represented consistently and safely in the Flutter app.

Out of scope for Feature 005:
- Real HTTP wiring to a deployed runtime.
- Auth token acquisition or Microsoft sign-in.
- Backend route implementation.
- Dataverse, solution, or campaign status calculation.
- UI screen completion beyond whatever minimal harness is needed to prove client use.

Expected measurable outcomes:
- Every draft `/v1/admin/*` operation has a typed Dart method.
- Every Admin API schema listed above has a Dart representation or documented equivalent.
- Tests cover each mock method and at least one error response path.
- Fixture data can drive the Feature 004 app shell without live services.

Specification instructions:
- Write the spec as requirements, not an implementation plan.
- Include the required Bench Owner field with `flutterBench`.
- State that this feature consumes the OpenAPI draft and does not modify Python runtime behavior except for documentation if needed.
- Make contract drift handling explicit: generated/manual client updates must be traceable to the OpenAPI file.
```
