# Contract: Transcript Redaction Layer

> Python-flavored pseudo-code for readability; the authoritative contract is the prose.

**Module boundary**: spec FR-028–FR-030; constitution principle V (minimize sensitive data)
**Implementation**: `src/opencloser/redaction/layer.py`
**Owns**: transforming transcript text before any transcript artifact disk write, and
enforcing the configured retention mode
**MUST NOT contain**: persona logic, CRM logic, transport logic, session lifecycle

---

## Public surface

```text
RedactionLayer:
    redact(transcript_text: str) -> str
        # Applies the configured policy. NoOp policy returns the text unchanged.

    retention_mode() -> "full" | "summary-only"
        # When "summary-only", no full transcript file is written at all.

Policies: RegexRedactionPolicy (default) | NoOpPolicy
```

---

## Behavior

The artifact writer (`src/opencloser/artifacts/writer.py`) calls the layer immediately
before writing the transcript artifact:

1. **`retention_mode() == "full"`**: write `redact(transcript_text)` to the transcript file.
   - `RegexRedactionPolicy` (default): replace every match of the configured patterns
     (phone numbers, emails, …) with `[REDACTED]` (FR-028).
   - `NoOpPolicy`: return text unchanged; the artifact contract (summary + transcript
     pointer) is identical to Slice 1 (FR-029).
2. **`retention_mode() == "summary-only"`**: write **no** full transcript file; the
   session-result artifact still carries the normalized summary and records
   `retention_mode = "summary-only"` (FR-030).
3. The session-result artifact's summary and transcript-pointer fields are preserved in all
   modes (FR-029). The pointer is null/omitted under summary-only retention.

Policy and retention mode come from `config/slice2.toml [redaction]`. The layer is
**default-on**: turning redaction off requires an explicit `policy = "noop"` — it cannot be
silently disabled (spec §Assumptions §"Redaction default").

> **Two layers, two defaults — do not conflate (added by /speckit-analyze I3, 2026-05-25):**
>
> 1. The **Slice 2 config-driven layer** built by the runner's readiness gate via
>    `RedactionLayer.from_config(slice2_config.redaction)` is what "default-on" refers to.
>    The Slice 2 config defaults (`policy = "regex"`, retention `"full"`, patterns =
>    `_BUILTIN_REDACTION_PATTERNS`) ensure transcripts are redacted whenever the Slice 2
>    runner is the caller. This is the path the spec/plan/research all describe.
> 2. The **writer's silent fallback** (`artifacts/writer.py:_DEFAULT_REDACTION_LAYER`) is
>    a **`NoOpPolicy + "full"` retention** layer (`RedactionLayer.noop()`), used only
>    when a direct caller invokes `write_session_artifacts` *without* an explicit
>    `redaction_layer=` kwarg. This preserves Slice 1's pre-Slice-2 behavior (Slice 1
>    deferred redaction to Slice 2 entirely), so Slice 1 tests and callers that predate
>    this contract are NOT silently opted into redaction they never asked for. Closed
>    Copilot PR #3 LOW on commit `0a5b3b7`; the unit test
>    `tests/unit/test_artifacts_writer.py::test_writer_without_explicit_layer_does_not_redact`
>    pins the no-PII-leak property.
>
> Slice 2 callers MUST pass the configured layer explicitly (the runner already does so via
> readiness). The writer's silent fallback is a backstop, not the Slice 2 default.

The layer is pure with respect to openCloser state — its only effect is the returned string
and the writer's retention decision.

---

## Dependencies

- **Allowed**: `opencloser.models` (`RedactionPolicyConfig`), stdlib `re`.
- **Forbidden**: `opencloser.crm.*`, `opencloser.transport`, `opencloser.persona`,
  `opencloser.core`, `opencloser.state`.
