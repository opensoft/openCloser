# Dograh and Runtime Architecture Decision

Status: Accepted

Last updated: 2026-05-24

## Decision

openCloser will keep its live-call runtime centered on direct speech-to-speech
audio through the configured real-time model provider, initially through the
Pipecat runtime adapter. Dograh will not become the core openCloser runtime,
CRM source of truth, campaign system, or operator UI for the MVP.

Dograh may be evaluated as a sidecar only when the sidecar is behind an
explicit runtime adapter boundary:

```text
openCloser CRM queue -> openCloser session -> Dograh sidecar run -> normalized outcome -> openCloser CRM write-back
```

In that mode, openCloser still owns the queue claim, eligibility decision,
session ID, correlation IDs, final disposition, and CRM write-back. Dograh
would be treated as an external runtime experiment that returns transcript,
event, and outcome data.

## Rationale

openCloser is CRM-first. Dynamics remains the operator surface and the durable
business source of truth. Pulling in Dograh as the main application would add a
parallel workflow UI, campaign model, auth surface, database stack, telemetry
surface, and deployment footprint before the MVP proves the CRM-owned call loop.

The live-call latency target also favors a direct audio model path. The normal
modular voice-agent chain adds separate STT, LLM, and TTS provider hops. The
MVP should instead use the real-time model for the live conversation and keep
secondary STT as a verification and audit lane.

## Adopted Dograh-Inspired Patterns

openCloser should copy or adapt these product patterns, not Dograh's whole app:

- Workflow/run ergonomics: clear persona versions, run records, event streams,
  tool events, and post-run outcomes.
- Latency observability: measure user-stop-speaking to bot-start-speaking,
  service TTFB, tool-call duration, and maximum per-turn latency.
- Developer test loop: run one test call or fixture, inspect transcript/events,
  and see the normalized CRM write-back payload before live dialing.
- Optional sidecar experiment: compare Dograh's workflow builder speed and
  runtime behavior without giving it CRM authority.

## Shadow STT Lane

The Slice 3 runtime should support a non-blocking shadow STT lane.

Primary live path:

```text
caller audio -> SignalWire -> Pipecat -> realtime model -> audio response
```

Shadow verification path:

```text
same caller audio -> shadow STT provider -> shadow transcript -> discrepancy events
```

The shadow lane must not block live conversation in the MVP. It records a
second transcript and compares it with the realtime model transcript/log for
high-value fields:

- opt-out or do-not-call request
- wrong-number indication
- email address
- callback time or callback intent
- person reached name and role
- interest level and final disposition

Early versions should record discrepancies and route uncertain results to
human review. Later versions may use discrepancies as policy inputs for safety
gates, disposition confidence, or CRM write-back confidence.

## Constraints

- Dograh must not create or update CRM records directly in the MVP.
- Dograh must not introduce a custom campaign/operator UI as a required pilot
  surface.
- Dograh sidecar runs must use openCloser correlation IDs and return normalized
  events.
- Any Dograh container or code reuse must be reviewed for third-party license,
  telemetry, PHI, and packaging implications before distribution or production
  handling of sensitive data.
- Shadow STT transcript storage must follow the same retention and redaction
  policy as primary transcripts.

