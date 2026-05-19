# Phase 0 Research: Slice 1 — Mock Call, Mock CRM

**Plan**: [plan.md](./plan.md)
**Spec**: [spec.md](./spec.md)
**Created**: 2026-05-19

Each decision below resolves an item from spec.md's `## Deferred to Implementation Plan` section or a tech choice not pinned by the spec. Format: **Decision** / **Rationale** / **Alternatives considered**.

---

## Language & runtime

**Decision**: Python 3.12+ (target `>=3.12,<3.14`).

**Rationale**:
- The broader openCloser stack converges on Python: Pipecat (Slice 2+), SignalWire's Python SDK is first-class, healthcare-AI and NLP libraries are dominantly Python, future LLM integration is straightforward.
- Slice 1 needs SQLite + JSON + a CLI + scripted-state-machine persona — Python's stdlib covers most of this directly.
- Python 3.12 gives `tomllib` (stdlib TOML reader), `datetime` with full UTC support, and improved type-narrowing for Pydantic-style validation. 3.13 is supported as well; 3.14 is too new to require.
- Single-language repo simplifies the future Pipecat / SignalWire integration boundary.

**Alternatives considered**:
- **Node.js / TypeScript**: would shorten ramp for any future React/Next.js work but creates a stack split with Pipecat and SignalWire Python SDKs. Rejected.
- **Go**: excellent SQLite story (modernc/sqlite, zombiezen/sqlite) and great test ergonomics, but pulls away from the AI/telephony ecosystem. Rejected.
- **Rust**: overkill for an MVP slice; slower iteration. Rejected.

---

## Build & package management

**Decision**: `uv` for environment + dependency management; `pyproject.toml` (PEP 621) for metadata.

**Rationale**:
- `uv` is the current state-of-the-art Python package/runner — fast, reproducible, lockfile-driven, no need for `pip-tools` or `poetry` add-ons.
- PEP 621 keeps metadata in `pyproject.toml`, the standard location.
- `uv run` works as a script runner so `uv run opencloser-cli ...` is the canonical entry point during development.

**Alternatives considered**:
- **Poetry**: long-standing, but slower and more opinionated than `uv`. Rejected.
- **pip + venv + requirements.txt**: maximum portability, weakest reproducibility. Rejected.
- **Hatch**: solid, but `uv` has lower setup cost for new contributors. Rejected.

---

## CLI framework

**Decision**: Typer.

**Rationale**:
- Typer wraps Click with type-hint-driven argument parsing — every CLI option is annotated, validated, and auto-documented.
- First-class Pydantic interop (we use Pydantic v2 for entities).
- The Slice 1 CLI is small (one or two commands); Typer keeps boilerplate minimal.

**Alternatives considered**:
- **Click**: more mature; chosen if Typer's auto-doc were not a win. Rejected for ergonomics.
- **argparse**: stdlib, zero deps, but verbose. Rejected.
- **Fire**: too magical for a spec-driven slice. Rejected.

---

## State store

**Decision**: SQLite via stdlib `sqlite3`, schema in `src/opencloser/state/schema.sql`, thin DAO in `state/store.py`.

**Rationale**:
- Mandated by spec.md `## Assumptions → Local state store`.
- stdlib `sqlite3` is sufficient for Slice 1's single-process, single-record workload — no ORM needed.
- A thin DAO layer (one function per query) keeps the schema visible and reviewable, and gives the future Slice 2 migration story a clear inflection point.
- WAL mode + foreign-keys-on are set as PRAGMAs at connection time so durability and referential integrity hold.

**Alternatives considered**:
- **SQLAlchemy**: production-grade ORM, but heavy for Slice 1 and creates schema-by-Python-class drift. Rejected.
- **peewee**: lightweight ORM, but the DAO + raw SQL approach is easier to audit. Rejected.
- **SQLModel**: combines Pydantic + SQLAlchemy. Promising, but uses SQLAlchemy under the hood. Defer to Slice 2 if a real ORM becomes attractive.

---

## Entity validation & serialization

**Decision**: Pydantic v2 (`pydantic >=2.7`).

**Rationale**:
- The spec mandates strict shapes for FR-014 (Normalized Result), FR-028 (Phone Call activity), FR-029 (queue-status update), FR-030 (Task payload), and FR-031 (per-disposition write-back mapping). Pydantic enforces these at runtime with low ceremony.
- v2's `model_dump_json(by_alias=True, exclude_none=True)` gives us a clean exported-artifact representation in one call.
- Pydantic's `Annotated[...]` lets us pin ISO 8601 / UTC / millisecond timestamps via a single shared `Annotated[datetime, AfterValidator(...)]` type.
- Plays well with Typer.

**Alternatives considered**:
- **dataclasses + custom validators**: stdlib-only but every field-level validator + serializer is hand-rolled. Rejected.
- **attrs + cattrs**: comparable to Pydantic but smaller ecosystem and less FastAPI alignment for future slices. Rejected.
- **msgspec**: very fast, but Pydantic v2 is fast enough for Slice 1 and is far more familiar. Rejected.

---

## Configuration surface

**Decision**: `config/slice1.toml` read via stdlib `tomllib`, with environment-variable overrides for every top-level key (env var prefix `OPENCLOSER_`).

**Rationale**:
- TOML is human-friendly, comment-supporting, and stdlib-readable in 3.12.
- `OPENCLOSER_CALL_WINDOW_START`, `OPENCLOSER_MAX_ATTEMPTS`, `OPENCLOSER_DEFAULT_TIMEZONE`, `OPENCLOSER_ARTIFACT_DIR` make CI / container overrides trivial.
- The TOML file in `config/` is the canonical default; per-environment overrides live in env vars or a `slice1.local.toml` (gitignored). Both layers are merged at startup, with env vars winning.

**Config keys (Slice 1)**:

```toml
# config/slice1.toml
[call_window]
start = "09:00"
end = "20:00"

[eligibility]
max_attempts = 5
default_timezone = "America/Los_Angeles"

[artifacts]
dir = "./artifacts"
schema_version = "slice1-v1"

[persona]
version = "alf-appointment-setter@0.1.0"
```

**Alternatives considered**:
- **YAML**: more permissive but needs `pyyaml`, and TOML is now standard. Rejected.
- **JSON**: no comments, friction for hand-edits. Rejected.
- **env vars only**: weakest for documentation. Rejected.

---

## Persona fixture format

**Decision**: One JSON file per scripted-conversation outcome, structured as an ordered list of turns where each turn is `{ "role": "persona" | "contact", "text": "..." }`. Branching is modeled by separate fixture files per branch (one fixture per supported disposition; see project structure in plan.md).

**Rationale**:
- A flat turn-list is the simplest representation that the persona module can iterate over deterministically. Slice 1 doesn't need a branching DSL — there's no live LLM and no real-time decision-making — so each disposition gets its own fixture file.
- JSON is readable and matches the rest of the artifact pipeline.
- The persona's extraction (FR-034) is performed against the *contact* turns; the persona's *persona* turns are validated against the disclosure / allowed-claims rules.

**Schema (per fixture file)**:

```json
{
  "fixture_id": "interested_callback_requested",
  "expected_disposition": "interested_callback_requested",
  "queue_item_ref": "alf-prospect-001",
  "turns": [
    { "role": "persona", "text": "Hi, this is an AI assistant calling on behalf of Medx ..." },
    { "role": "contact", "text": "Sure, what's this about?" },
    { "role": "persona", "text": "..." },
    { "role": "contact", "text": "Yeah, give me a callback Thursday at 2 PM." }
  ],
  "expected_extraction": {
    "callback_requested": true,
    "preferred_callback_window": "Thursday 14:00"
  }
}
```

`expected_disposition` and `expected_extraction` are used in unit-test assertions; they are NOT inputs to the persona.

**Alternatives considered**:
- **YAML state-machine descriptors**: more expressive but overkill for Slice 1. Rejected.
- **Plain-text transcripts with `[CONTACT]` / `[PERSONA]` prefixes**: cheaper to author but harder to validate. Rejected.
- **One fixture file with branching**: would couple all dispositions together. Rejected for clarity.

---

## Mock transport fixture format

**Decision**: One JSON file per transport-path scenario, listing the event sequence the mock transport emits in order.

**Schema**:

```json
{
  "fixture_id": "no_answer",
  "events": [
    {
      "event_id": "evt-001",
      "type": "no_answer",
      "timestamp": "2026-05-19T17:00:01.000Z",
      "payload": {}
    }
  ]
}
```

Duplicate-event scenarios repeat the same `event_id`; conflicting-late-event scenarios append events after a finalizing event.

**Rationale**: keeps the transport's interface uncluttered — the mock transport simply yields the events in file order. The `event_id` is the FR-019 idempotency anchor.

**Alternatives considered**: same as persona fixtures; rejected for the same reasons.

---

## Artifact directory & filenames

**Decision**:

- Directory: `./artifacts/{session_id}/` (configurable via `OPENCLOSER_ARTIFACT_DIR`).
- Files inside the session's directory:
  - `session-result.json` (FR-014 fields)
  - `writeback.json` (the three CRM payloads under `phone_call_activity`, `queue_status_update`, `task` keys; only `queue_status_update` is always present)
  - `task.json` (the standalone Task payload, when emitted — duplicates the `writeback.json` content for operator convenience)
  - `transcript.txt` (the scripted-fixture transcript, plain text, one turn per line as `[ROLE] TEXT`)
  - `eligibility-decision.json` (always emitted; lists every rule's pass/fail and any failing-rule names)
  - `conflicting-events.json` (only emitted when at least one conflicting late event arrived; per FR-020)

**Rationale**:
- Per-session subdirectory keeps a single run's files together (operator-friendly per SC-007).
- Filenames are short, predictable, and case-insensitive distinct (Windows-safe).
- FR-023's "filenames MUST allow correlation by session ID" is satisfied by the parent directory; intra-directory filenames are fixed.
- The eligibility-decision artifact is its own file so blocked-by-eligibility runs (which produce no Phone Call activity) still give operators a readable block reason per Story 2.

**Alternatives considered**:
- **Flat layout `{session_id}-{kind}.json`**: simpler for `ls` but operator scan becomes noisy when many sessions exist. Rejected.
- **Single combined JSON per run**: hides the per-payload structure that the future Dataverse adapter must mirror. Rejected.

---

## JSON serialization

**Decision**: 2-space indented, `sort_keys=True`, UTF-8, no BOM, LF line endings.

**Rationale**:
- Indented + sorted keys produces deterministic, diffable output — vital for fixture-driven test snapshots and for the SC-005 "duplicate event leaves artifact unchanged" check.
- UTF-8 + no BOM + LF maximizes cross-platform readability (FR-023 "readable").

**Implementation**: a small `artifacts/writer.py::write_json(path, obj)` wrapper around `pydantic.BaseModel.model_dump(mode="json")` + `json.dumps(..., sort_keys=True, indent=2, ensure_ascii=False)`. Writes via `tmp + os.replace` for atomicity.

**Alternatives considered**:
- **Minified JSON**: smaller, but harms SC-007. Rejected.
- **JSONL / NDJSON**: useful for streaming, irrelevant for one-record-per-run. Rejected.

---

## Schema versioning

**Decision**: every exported JSON artifact carries `"schema_version": "slice1-v1"` at the top level.

**Rationale**: forward-looking — Slice 2 / Dataverse may need to evolve payload shapes. The version field is the single signal future readers use to dispatch. `slice1-v1` is the initial value; bump policy is "increment the trailing number on any backwards-incompatible change to any artifact's required fields".

**Alternatives considered**:
- **Per-artifact version fields** (`session_result_v1` / `writeback_v1` / ...): more granular, more bookkeeping. Rejected for Slice 1.
- **No version field, infer from spec**: brittle. Rejected.

---

## `persona_version` format

**Decision**: `alf-appointment-setter@MAJOR.MINOR.PATCH` (semver, prefixed by persona name).

**Rationale**:
- FR-011 mandates the persona is versioned and FR-036 mandates deterministic behavior — semver makes "did the rules change?" explicit. `MAJOR` increments on disposition-rule precedence changes; `MINOR` on disclosure-language changes; `PATCH` on bug fixes that preserve observable behavior.
- Prefixing with the persona name future-proofs against additional personas in Slice 3+.
- Stored as a string in the session's `persona_version` column and copied into all FR-028 / FR-030 payloads.

**Initial value**: `alf-appointment-setter@0.1.0`.

**Alternatives considered**:
- **ISO date string**: doesn't carry behavioral semantics. Rejected.
- **Content hash of the disposition-rules module**: clever but opaque to humans. Rejected.

---

## Tests & CI gates

**Decision**: pytest with module-scoped markers, dependency-direction lint, and coverage floor.

**Approach**:
- One `tests/unit/test_<module>.py` per FR-033 module, marked `@pytest.mark.module("<name>")`. CI runs each marker in isolation against stubs to satisfy SC-009.
- Integration tests in `tests/integration/test_end_to_end.py` cover Story 1, Story 2, Story 3, SC-001 through SC-007. SC-008 (Slice 2 forward-compat) is deferred; SC-009 is the module-isolation gate above.
- Coverage floor: 90% for `src/opencloser/` excluding `__init__.py`.
- Dependency-direction lint: a small custom script that checks the AST of each module's `import` statements to enforce "core can import all four boundary modules; boundary modules can import `models` and `state` but NOT each other". Implemented in `tests/test_imports.py`.

**Rationale**: SC-009 is the single most boundary-defining success criterion, so we make it cheap to verify. The dependency-direction check is the static-analysis half; the per-module test runs are the runtime half.

**Alternatives considered**:
- **Pyright / mypy for boundary enforcement**: powerful but heavy. Defer to a later slice if static typing becomes a project-wide bar.
- **architest / pytest-archon**: real tools for architecture testing in Python; consider in Slice 2 if the hand-rolled check feels brittle.

---

## Tooling

**Decision**: ruff for both lint and format (`ruff check` + `ruff format`). No black, no isort, no flake8 — ruff covers all three.

**Rationale**: single tool, single config, fast, modern. Aligns with `uv`.

**Alternatives considered**: black + isort + flake8 — three tools where one suffices. Rejected.

---

## Performance / observability

**Decision**: no observability infrastructure beyond exported artifacts and CLI output in Slice 1; SC-001's 60-second budget is measured by the CLI emitting `wall_time_ms` in its final summary line.

**Rationale**: spec.md is light on observability requirements beyond FR-023 / FR-027; that's intentional for Slice 1. Real logging / metrics / tracing land in Slice 2 alongside the real transport. The CLI's wall-time line is the minimal SC-001 instrumentation.

**Alternatives considered**: structured logging (`structlog`) — useful but premature for Slice 1.

---

## Cross-cutting decisions

### Atomic artifact writes
All artifact files are written via `tempfile.NamedTemporaryFile(dir=session_dir, delete=False)` followed by `os.replace(tmp, final)`. This ensures crash-safety and gives FR-019's "duplicate events MUST be no-ops on exported artifacts" a clean fast-path: re-export is allowed because the bytes are deterministic (per the JSON serialization decision).

### Idempotency check ordering
The orchestrator's loop is: (1) compute idempotency key, (2) check the `idempotency_keys` table, (3) if present, log and return; if absent, execute the state change inside a transaction that also inserts the idempotency key. This makes the no-op behavior trivially correct.

### Timestamps
A single `now_utc_ms()` helper in `core/orchestrator.py` is the only source of timestamps. Tests inject a frozen clock through a `Clock` protocol in `core/`.

---

## Resolved-spec-deferrals checklist

Every item from spec.md `## Deferred to Implementation Plan` has a corresponding decision above. Cross-reference:

| Deferred item | Resolved by |
|---|---|
| Artifact filename pattern | §Artifact directory & filenames |
| Artifact directory location | §Artifact directory & filenames |
| Per-session subdirectory | §Artifact directory & filenames |
| JSON serialization style | §JSON serialization |
| Timestamp serialization library | §Cross-cutting decisions → Timestamps |
| Schema-versioning marker | §Schema versioning |
| Configuration file location and format | §Configuration surface |
| Configuration validation | §Configuration surface (Pydantic v2 over the TOML dict at startup) |
| Persona fixture format | §Persona fixture format |
| Fixture-loading mechanism | §Persona fixture format + plan.md project structure |
| Module package boundaries in code | plan.md §Project Structure |
| `persona_version` string format | §`persona_version` format |
| State store schema | data-model.md |
| Determinism guarantees of the persona module | §Persona fixture format + FR-036 |
| CI gates for module isolation (SC-009) | §Tests & CI gates |
| Fixture catalog for SC-003 | plan.md §Project Structure → `tests/fixtures/conversations/` |
| Performance instrumentation for SC-001 | §Performance / observability |
