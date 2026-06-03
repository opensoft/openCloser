# Feature 007 Speckit Specify Prompt

Run from the root checkout while on `main`. OpenSpec/Speckit shell commands
should run from `py-bench`; the root checkout there is
`/workspace/projects/openCloser`. This feature is owned by `flutterBench` for
implementation after the spec is created.

```text
GIT_BRANCH_NAME=007-admin-environment-install-checklist SPECIFY_FEATURE_DIRECTORY=specs/007-admin-environment-install-checklist /speckit.specify Create Feature 007: Admin Environment Selection and Install Checklist.

Generate the Speckit feature specification for openCloser Feature 007. This feature builds Flutter screens for Dataverse environment selection and install verification checklist using the Feature 005 client boundary and mock adapters.

Authoritative context:
- `.specify/memory/constitution.md`
- `specs/README.md`
- `docs/architecture/openCloser_Client_Onboarding_and_Admin_App.md`
- `docs/architecture/openCloser_Release_and_Repo_Strategy.md`
- `docs/prds/openCloser_MVP.md`
- `docs/prds/openCloser_PRD.md`
- `integrations/dynamics365/README.md`
- `integrations/dynamics365/docs/configuration.md`
- `integrations/dynamics365/docs/install.md`
- `contracts/opencloser-runtime-v1.openapi.yaml`
- `specs/004-admin-flutter-scaffold/speckit-specify-prompt.md`
- `specs/005-admin-openapi-client-mocks/speckit-specify-prompt.md`
- `specs/006-admin-account-consent-flow/speckit-specify-prompt.md`

Feature 007 target slice:
- Bench owner: `flutterBench`.
- Target phase: Flutter admin CRM selection and install verification UX.
- Goal: let a client admin select a Dataverse environment and inspect a checklist for managed solution, environment variables, Dataverse access, trigger reachability, and dry-run smoke status using mock API responses.
- The smallest independently demonstrable outcome is: a tester can select a mocked environment and see passing, failing, warning, skipped, permission-gap, unavailable, not-installed, installed, and update-available checklist states.
- This feature must be fully owned by `flutterBench`. Do not implement Dataverse discovery, solution detection, Power Platform automation, or Python verification endpoints.

Required scope:
- Build environment list and selection UI using `CrmEnvironment`.
- Build CRM environment status UI using `CrmEnvironmentStatus` and `SolutionStatus`.
- Build install verification checklist UI using `VerificationReport` and `VerificationCheck`.
- Cover required checks: tenant consent, account active, runtime reachable, CRM reachable, managed solution installed/version, environment variables present, metadata read access, Lead trigger, Campaign trigger, dry-run smoke test, optional write-enabled test lead.
- Show solution status: not installed, installed, update available, unknown/failing.
- Show Dataverse access status: connected, permission gap, unavailable.
- Provide retry/re-run verification state and user-safe error handling from `Problem`.
- Keep all CRM business-record editing out of scope.
- Add Flutter tests for environment selection, checklist pass, checklist failure, warnings/skipped checks, and empty environment list.

User stories the generated spec should cover:
- A client admin can choose the Dynamics/Dataverse environment that openCloser should connect to.
- A client admin can see whether the openCloser managed solution is installed and which version is present.
- A client admin can inspect install readiness checks and identify what needs attention.
- A support user can reproduce install failure states through deterministic mocks.

Out of scope for Feature 007:
- Real Dataverse environment discovery.
- Managed solution import/export/packaging.
- Runtime verification endpoint implementation.
- Account/consent screens except as prerequisites/navigation context.
- Health dashboard and campaign controls.

Expected measurable outcomes:
- Environment selection renders populated, empty, permission-gap, and unavailable states.
- Verification checklist renders passing, failing, warning, and skipped checks.
- Solution status distinguishes installed/not installed/update available.
- Tests cover the main checklist and environment states without live CRM.

Specification instructions:
- Write the spec as requirements, not an implementation plan.
- Include the required Bench Owner field with `flutterBench`.
- State that this feature consumes mocked Admin API data and does not implement backend verification.
- Keep the checklist precise enough to map to `/v1/admin/crm/environments/{environment_id}/verify` later.
```
