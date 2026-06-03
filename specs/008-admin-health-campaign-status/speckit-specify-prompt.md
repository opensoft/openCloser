# Feature 008 Speckit Specify Prompt

Run from the root checkout while on `main`. OpenSpec/Speckit shell commands
should run from `py-bench`; the root checkout there is
`/workspace/projects/openCloser`. This feature is owned by `flutterBench` for
implementation after the spec is created.

```text
GIT_BRANCH_NAME=008-admin-health-campaign-status SPECIFY_FEATURE_DIRECTORY=specs/008-admin-health-campaign-status /speckit.specify Create Feature 008: Admin Health and Campaign Status.

Generate the Speckit feature specification for openCloser Feature 008. This feature builds Flutter admin health dashboard, active campaign summary, failures needing attention, and pause/resume controls using mock adapters.

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
- `specs/007-admin-environment-install-checklist/speckit-specify-prompt.md`

Feature 008 target slice:
- Bench owner: `flutterBench`.
- Target phase: Flutter admin status and light controls UX.
- Goal: provide a compact admin overview of account, tenant consent, CRM extension, Dataverse access, runtime API, telephony, AI runtime, write-back, campaign status, and pause/resume controls.
- The smallest independently demonstrable outcome is: a tester can open the Flutter dashboard with mock health and campaign data, see degraded areas, inspect campaign counts, and exercise mocked pause/resume actions.
- This feature must be fully owned by `flutterBench`. Do not implement backend campaign status calculation, runtime health endpoints, CRM writes, or campaign automation.

Required scope:
- Build system health dashboard from `AdminHealth`.
- Represent statuses for account, tenant consent, CRM extension, Dataverse access, runtime API, telephony, AI runtime, and write-back.
- Build campaign list/status UI from `CampaignSummary`.
- Show campaign statuses: active, paused, blocked, test mode.
- Show eligible lead count, calls attempted today, and failures needing attention.
- Add pause/resume control UI through mock `pauseCampaign` and `resumeCampaign` client methods.
- Show action-disabled states when account, consent, Dataverse, runtime, or campaign status blocks control use.
- Keep controls narrow: pause/resume only, no campaign builder or CRM record editing.
- Add Flutter tests for healthy, degraded, unavailable, empty campaign list, pause, resume, and failed action states.

User stories the generated spec should cover:
- A client admin can see overall openCloser health at a glance.
- A client admin can identify which subsystem needs attention when setup is degraded.
- A client admin can see active campaigns and basic counts without leaving the admin app.
- A client admin can pause or resume campaign automation through mocked controls.
- A support user can reproduce healthy, degraded, blocked, and unavailable states through deterministic mocks.

Out of scope for Feature 008:
- Real `/v1/admin/health` or `/v1/admin/campaigns` backend implementation.
- Real pause/resume effects in CRM or runtime workers.
- Detailed analytics, reporting, transcript review, call detail drilldown, lead editing, or campaign building.
- Push notifications.

Expected measurable outcomes:
- Dashboard renders every `AdminHealth` area with normal/degraded/unavailable visual states.
- Campaign list renders active, paused, blocked, and test-mode states.
- Mock pause/resume updates are visible and reversible in the UI.
- Tests cover health, campaign, and pause/resume paths without live backend.

Specification instructions:
- Write the spec as requirements, not an implementation plan.
- Include the required Bench Owner field with `flutterBench`.
- Preserve the admin boundary: overview and pause/resume controls only.
- State that Feature 009/010 own backend health and campaign data.
```
