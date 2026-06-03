# Feature 004 Speckit Specify Prompt

Run from the root checkout while on `main`. OpenSpec/Speckit shell commands
should run from `py-bench`; the root checkout there is
`/workspace/projects/openCloser`. This feature is owned by `flutterBench` for
implementation after the spec is created.

```text
GIT_BRANCH_NAME=004-admin-flutter-scaffold SPECIFY_FEATURE_DIRECTORY=specs/004-admin-flutter-scaffold /speckit.specify Create Feature 004: Admin Flutter Scaffold.

Generate the Speckit feature specification for openCloser Feature 004, the first Flutter admin app feature. This feature creates the admin app shell only: Flutter project setup, routing, theme, responsive layout, fixture-backed navigation, and core UI states.

Authoritative context:
- `.specify/memory/constitution.md`
- `specs/README.md`
- `docs/prds/openCloser_MVP.md`
- `docs/prds/openCloser_PRD.md`
- `docs/architecture/openCloser_Client_Onboarding_and_Admin_App.md`
- `docs/architecture/openCloser_Release_and_Repo_Strategy.md`
- `docs/architecture/openCloser_Architecture.md`
- `contracts/opencloser-runtime-v1.openapi.yaml`

Feature 004 target slice:
- Bench owner: `flutterBench`.
- Target phase: Flutter admin app scaffold, post-Feature-002 and parallel to Feature 003.
- Goal: create a demoable Flutter admin shell under the temporary in-repo path `apps/admin_flutter/` without live auth, live CRM, or live backend dependencies.
- The smallest independently demonstrable outcome is: a developer can run the Flutter app locally and navigate between admin shell screens using fixture data, with loading, empty, error, and normal UI states represented.
- This feature must be fully owned by `flutterBench`. Do not add Python runtime endpoints, Dataverse integration, SignalWire/Pipecat work, Dynamics managed-solution packaging, or real Microsoft auth.

Product boundary:
- The admin app is an install and operations surface only.
- It must not become the operator campaign UI, CRM replacement, task queue, transcript console, analytics dashboard, or campaign builder.
- The pilot operator UI remains Dynamics.
- The Flutter app should be mobile-first and tablet/web-ready from the same codebase.

Required scope:
- Create the Flutter project scaffold at `apps/admin_flutter/`.
- Define app routing for account setup, consent, environment selection, install checklist, health, campaigns, and settings/status surfaces, even if later screens are placeholders backed by fixtures.
- Establish theme, typography, color tokens, spacing, icons, responsive breakpoints, and accessible tap targets suitable for a quiet operational admin tool.
- Provide reusable shell components: app frame, navigation, status banner, loading state, empty state, error state, retry action, and compact status indicators.
- Add fixture-backed navigation and sample state objects so UI work can continue before backend APIs exist.
- Add basic Flutter tests or golden/smoke checks appropriate for the scaffold.
- Document how to run the app in `flutterBench`.

User stories the generated spec should cover:
- A client admin can open the Flutter admin app and see a coherent account/install/status shell.
- A developer can navigate through all planned admin routes using fixture state without any live backend.
- A user can recognize loading, error, empty, and healthy states consistently across the app.
- The app adapts cleanly across phone, tablet, and web-sized layouts without text overlap or inaccessible controls.

Out of scope for Feature 004:
- Generated OpenAPI client and typed API models beyond minimal local fixtures.
- Microsoft sign-in, tenant consent, or Entra integration.
- Real `/v1/admin/*` runtime calls.
- Dataverse environment discovery, solution verification, health calculation, campaign pause/resume behavior, or backend fixture server work.
- Python runtime implementation.
- Dynamics managed-solution packaging.

Expected measurable outcomes:
- Flutter app launches from `apps/admin_flutter/` in `flutterBench`.
- All planned top-level admin routes are reachable using fixture navigation.
- Shared UI states render without backend calls.
- Responsive smoke checks cover at least phone and tablet/web widths.
- No screen presents itself as a CRM operator workflow or campaign builder.

Specification instructions:
- Write the spec as a requirements document, not an implementation plan.
- Include the required Bench Owner field with `flutterBench`.
- Make clear that backend/API behavior is mocked or fixture-only in this feature.
- Keep the app narrow: install, health, and light campaign visibility only.
- Define acceptance criteria that can be verified without live CRM, live auth, or live runtime APIs.
```
