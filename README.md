# openCloser

A CRM-first AI communication platform for healthcare-oriented outreach.

## Feature Status

Current shipped runtime slices:

- Feature 001 — Slice 1: mock call, mock CRM.
- Feature 002 — Slice 2: mock call, real CRM.

See:

- [Feature inventory](specs/README.md) — feature numbering, bench ownership, and parallel Python/Flutter roadmap
- [Slice 1 specification](specs/001-mock-call-mock-crm/spec.md) — mock call plus mock CRM
- [Slice 2 specification](specs/002-mock-call-real-crm/spec.md) — mock call plus real CRM
- [Slice 1 quickstart](specs/001-mock-call-mock-crm/quickstart.md) — local mock-loop walkthrough
- [Constitution](.specify/memory/constitution.md) — binding project principles
- [Client onboarding/admin app](docs/architecture/openCloser_Client_Onboarding_and_Admin_App.md) — tenant install, Dynamics managed solution, and admin status surface
- [Release and repository strategy](docs/architecture/openCloser_Release_and_Repo_Strategy.md) — when to split admin and Dynamics packages into independently released repos
- [Dynamics integration scaffold](integrations/dynamics365/README.md) — managed-solution source area and CRM command-bar trigger scaffold

## Status

Feature 003 is reserved for the `py-bench` real-call/real-CRM runtime slice.
Flutter admin-app work starts at Feature 004+ and must stay in `flutterBench`
features so Python runtime and Flutter admin work can proceed in parallel.

## Bootstrap (developers)

```bash
uv sync
uv run opencloser init-state
uv run opencloser load-queue-item --file tests/fixtures/queue_items/alf-prospect-001.json
uv run opencloser run-one --queue-item-id alf-prospect-001 \
    --conversation-fixture tests/fixtures/conversations/interested_callback_requested.json \
    --transport-fixture tests/fixtures/transport_events/connected.json
```

See [`quickstart.md`](specs/001-mock-call-mock-crm/quickstart.md) for the full walkthrough.
