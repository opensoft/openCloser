# openCloser Feature Inventory

Status: Draft

Last updated: 2026-05-25

This index is the planning source of truth for Speckit feature numbering and
bench ownership. Each feature must be owned by exactly one bench:

- `py-bench` for Python runtime, API, worker, CRM, telephony, persona, and
  contract-test work.
- `flutterBench` for Flutter admin app UI, generated client, mock data layer,
  mobile/web packaging, and Flutter tests.

Do not mix Flutter and Python implementation tasks in one Speckit feature. When
a feature needs both sides, split it into a Flutter feature and a Python feature
that meet through `contracts/opencloser-runtime-v1.openapi.yaml` or another
versioned contract.

## Current Feature Ledger

| Feature | Bench | Status | Scope |
|---|---|---|---|
| 001 `mock-call-mock-crm` | `py-bench` | Shipped | Slice 1: local queue, mock call transport, mock CRM write-back, ALF persona fixtures, local artifacts. |
| 002 `mock-call-real-crm` | `py-bench` | Shipped | Slice 2: Dataverse queue/write-back, mock call transport, redaction, idempotent CRM write-back, dry-run/write-enabled demo. |
| 003 `real-call-real-crm` | `py-bench` | Next runtime feature | Slice 3: SignalWire outbound call, provider callbacks, Pipecat realtime audio path, direct realtime model, shadow STT discrepancy logging, hard phone-format enforcement, Dataverse write-back. No Flutter tasks. |

## Planned Features After 003

These numbers may be adjusted when each Speckit feature is created, but the
single-bench ownership must stay intact.

| Feature | Bench | Scope | Parallelization Notes |
|---|---|---|---|
| 004 `admin-flutter-scaffold` | `flutterBench` | Create the Flutter admin app shell, routing, theme, responsive layout, loading/error states, and fixture-backed navigation. | Can start while 003 is in progress because it uses local fixtures only. |
| 005 `admin-openapi-client-mocks` | `flutterBench` | Generate or hand-wrap the Runtime Admin API client from `contracts/opencloser-runtime-v1.openapi.yaml` and provide mock adapters for all `/v1/admin/*` flows. | Depends on the draft contract, not on live Python endpoints. |
| 006 `admin-account-consent-flow` | `flutterBench` | Microsoft sign-in entry, create/join account screens, tenant consent browser/deep-link states, and mocked account/tenant responses. | Builds on 004/005; no live Entra requirement. |
| 007 `admin-environment-install-checklist` | `flutterBench` | Dataverse environment selection plus install verification checklist for solution version, environment variables, access, command triggers, and dry-run smoke status. | Builds on 005 mocks; real runtime wiring comes later. |
| 008 `admin-health-campaign-status` | `flutterBench` | System health dashboard, active campaign summaries, eligible lead counts, failures needing attention, and pause/resume controls against mock adapters. | Can be demoed before backend admin APIs are complete. |
| 009 `runtime-admin-api-fixtures` | `py-bench` | Implement fixture-backed `/v1/admin/*` runtime endpoints and contract tests matching the OpenAPI draft so the Flutter app can leave pure mocks. | Can run in parallel with Flutter features after the OpenAPI client shape settles. |
| 010 `runtime-admin-api-dataverse` | `py-bench` | Replace admin fixture responses with real account, tenant consent, Dataverse environment, solution, verification, health, and campaign status integrations. | Backend integration feature; Flutter consumes the same API surface. |
| 011 `admin-real-api-integration` | `flutterBench` | Switch Flutter app from mock adapters to real runtime API configuration, auth callback handling, and integration-test fixtures. | Depends on 009 for fixture server; 010 for real tenant demos. |

## Bench Ownership Rules

- A `py-bench` feature may edit Python packages, runtime API contracts,
  Dataverse/SignalWire/Pipecat integrations, CLI commands, tests, docs, and
  fixtures needed to prove the runtime slice.
- A `flutterBench` feature may edit Flutter app code, Dart generated clients,
  Flutter fixtures, UI tests, screenshots, platform packaging, and admin-app
  docs.
- Shared contract changes must land in the feature that owns the contract
  source. Other features consume the contract as generated code or fixtures.
- CRM managed-solution work remains a separate Dynamics feature stream; do not
  hide Dynamics packaging tasks inside Flutter features or Feature 003.
- Feature 003 is the last MVP call-loop slice and must not absorb admin-app
  scaffold, dashboard, mobile packaging, or tenant-install UX tasks.
