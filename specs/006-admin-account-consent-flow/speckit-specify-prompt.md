# Feature 006 Speckit Specify Prompt

Run from the root checkout while on `main`. OpenSpec/Speckit shell commands
should run from `py-bench`; the root checkout there is
`/workspace/projects/openCloser`. This feature is owned by `flutterBench` for
implementation after the spec is created.

```text
GIT_BRANCH_NAME=006-admin-account-consent-flow SPECIFY_FEATURE_DIRECTORY=specs/006-admin-account-consent-flow /speckit.specify Create Feature 006: Admin Account and Consent Flow.

Generate the Speckit feature specification for openCloser Feature 006. This feature builds the Flutter admin account setup, Microsoft sign-in entry, create/join account flow, and tenant admin consent UI using the Feature 005 client boundary and mock adapters.

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

Feature 006 target slice:
- Bench owner: `flutterBench`.
- Target phase: Flutter admin onboarding UX.
- Goal: let a client admin walk through mocked Microsoft sign-in, create/join openCloser account, and tenant consent states without live Entra or backend dependencies.
- The smallest independently demonstrable outcome is: a tester can use the Flutter app to move from sign-in entry to account active/pending state to consent missing/pending/granted/failure states, all through mock client responses.
- This feature must be fully owned by `flutterBench`. Do not implement real Entra auth, backend consent verification, or Python account persistence.

Required scope:
- Build sign-in entry screen and signed-out/signed-in shell states.
- Build create/join account flow using `CreateAccountRequest` and `AccountResponse` mock data.
- Build tenant consent start and completion UI using `ConsentStartRequest`, `ConsentStartResponse`, `ConsentCompleteRequest`, and `TenantConsentStatus`.
- Represent consent states: missing, generated URL/pending browser handoff, granted, revoked/failure, and retry.
- Handle browser/deep-link intent as a UI state or mock callback flow without trusting URL parameters as verified truth.
- Show clear admin-facing status and next action without exposing developer-only implementation details.
- Preserve narrow admin scope: no campaign builder, CRM record editor, or operator task queue.
- Add Flutter widget or flow tests for account creation, consent success, consent failure, and retry.

User stories the generated spec should cover:
- A client admin can start the admin app, choose Microsoft sign-in, and reach account setup.
- A client admin can create or join an openCloser account and see account status.
- A client admin can start tenant consent and see the pending browser/deep-link state.
- A client admin can return from consent and see granted, revoked/failure, or retry states.
- A support user can reproduce account and consent edge cases with deterministic mocks.

Out of scope for Feature 006:
- Real Microsoft identity SDK integration.
- Real admin consent callback verification.
- Backend account creation or tenant persistence.
- Environment selection, install verification checklist, health dashboard, and campaign controls.
- Runtime API fixture server implementation.

Expected measurable outcomes:
- Account setup and consent routes are complete enough to demo with mock data.
- Account statuses `active`, `billing_pending`, and `suspended` have distinct UI handling.
- Tenant consent statuses `missing`, `granted`, and `revoked` have distinct UI handling.
- Tests cover at least success, pending, failure/revoked, and retry flows.

Specification instructions:
- Write the spec as requirements, not an implementation plan.
- Include the required Bench Owner field with `flutterBench`.
- State that real Microsoft auth and backend consent validation are later integration work.
- Keep the user language admin-oriented and avoid in-app explanatory tutorial copy beyond labels/status/action text.
```
