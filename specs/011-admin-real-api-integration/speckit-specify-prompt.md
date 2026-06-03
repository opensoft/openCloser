# Feature 011 Speckit Specify Prompt

Run from the root checkout while on `main`. OpenSpec/Speckit shell commands
should run from `py-bench`; the root checkout there is
`/workspace/projects/openCloser`. This feature is owned by `flutterBench` for
implementation after the spec is created.

```text
GIT_BRANCH_NAME=011-admin-real-api-integration SPECIFY_FEATURE_DIRECTORY=specs/011-admin-real-api-integration /speckit.specify Create Feature 011: Admin Real API Integration.

Generate the Speckit feature specification for openCloser Feature 011. This Flutter admin feature switches the app from pure in-app mocks to configurable real Runtime Admin API integration while preserving the mock adapter for tests and demos.

Authoritative context:
- `.specify/memory/constitution.md`
- `specs/README.md`
- `docs/architecture/openCloser_Client_Onboarding_and_Admin_App.md`
- `docs/architecture/openCloser_Release_and_Repo_Strategy.md`
- `docs/prds/openCloser_MVP.md`
- `docs/prds/openCloser_PRD.md`
- `contracts/opencloser-runtime-v1.openapi.yaml`
- `specs/004-admin-flutter-scaffold/speckit-specify-prompt.md`
- `specs/005-admin-openapi-client-mocks/speckit-specify-prompt.md`
- `specs/006-admin-account-consent-flow/speckit-specify-prompt.md`
- `specs/007-admin-environment-install-checklist/speckit-specify-prompt.md`
- `specs/008-admin-health-campaign-status/speckit-specify-prompt.md`
- `specs/009-runtime-admin-api-fixtures/speckit-specify-prompt.md`
- `specs/010-runtime-admin-api-dataverse/speckit-specify-prompt.md`

Feature 011 target slice:
- Bench owner: `flutterBench`.
- Target phase: Flutter admin real API wiring.
- Goal: allow the Flutter admin app to use a configured Runtime Admin API base URL, real HTTP transport, auth/consent callback state handling, robust error handling, and integration tests against the Feature 009 fixture server or Feature 010 real backend.
- The smallest independently demonstrable outcome is: a tester can point the Flutter app at a local fixture-backed runtime, complete the account/consent/environment/checklist/health/campaign flows through real HTTP calls, then switch back to mock mode for offline tests.
- This feature must be fully owned by `flutterBench`. Do not implement Python backend endpoints, Dataverse integrations, or contract-breaking API changes.

Required scope:
- Add runtime API base URL configuration for local fixture server, staging, and production-like environments.
- Add real HTTP transport behind the Feature 005 client interface.
- Preserve mock adapter selection for tests, demos, and offline development.
- Add request loading, timeout, retry, cancellation, and user-safe error states.
- Handle auth/consent callback state at the UI/client boundary without trusting URL parameters as backend-verified truth.
- Ensure account setup, consent, environment selection, install checklist, health dashboard, campaigns, and pause/resume screens can all use real HTTP responses.
- Add integration tests against the fixture-backed Admin API when available.
- Add diagnostics suitable for support without logging secrets, tokens, or sensitive CRM data.

User stories the generated spec should cover:
- A client admin can use the Flutter app against a configured Runtime Admin API instead of in-app mocks.
- A developer can run the Flutter app against the local fixture-backed runtime for repeatable integration testing.
- A tester can switch between mock and real API modes without code changes.
- Network failures, API `Problem` responses, timeouts, and unauthorized states render safely and consistently.
- Pause/resume and verification actions show pending, success, failure, and retry states based on real API responses.

Out of scope for Feature 011:
- Backend endpoint implementation.
- Dataverse or Microsoft integration logic.
- Changing the `/v1/admin/*` contract except for documented backwards-compatible additions approved in the runtime feature.
- App-store release automation, push notifications, broad analytics, transcript review, CRM record editing, or campaign builder features.

Expected measurable outcomes:
- The Flutter app can run in mock mode and real API mode from configuration.
- Real HTTP calls work against the Feature 009 fixture server for every admin flow.
- Error handling covers `Problem`, timeout, network unavailable, unauthorized, and unexpected response states.
- Integration tests exercise account, consent, environment, verification, health, campaign list, pause, and resume paths against a fixture server or recorded fixture transport.
- No secret/token values are persisted in logs or fixture output.

Specification instructions:
- Write the spec as requirements, not an implementation plan.
- Include the required Bench Owner field with `flutterBench`.
- State that backend implementation belongs to Feature 009/010 and this feature consumes the existing versioned contract.
- Preserve mock mode as a first-class path for repeatable UI tests.
```
