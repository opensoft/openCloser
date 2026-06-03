# AI Video Calls and Talking Head Rendering Research

Status: Research

Last updated: 2026-05-24

## Executive Summary

AI video calls should be treated as a post-MVP transport and presentation layer,
not as part of the ALF outbound caller MVP. The Interaction Core, persona
modules, transcript handling, audit events, and CRM write-back should remain the
same. The video stack should add:

- a WebRTC room or native app video transport
- a real-time audio conversation runtime
- an avatar renderer that turns the agent's output audio into a talking-head
  video track

OpenAI Realtime can handle low-latency audio and text interaction, but it does
not render a talking-head video output. The avatar must be a separate video
worker, provider, or client-side renderer.

Recommended research path:

1. Keep MVP phone calls on the existing direct realtime audio path.
2. For video-call research, prototype a WebRTC room with an avatar participant.
3. Compare a managed avatar provider against a simple browser-rendered avatar.
4. Keep clinical/doctor-avatar behavior behind a separate PRD, safety model,
   likeness policy, and compliance review.

## Reference Architecture

```text
User app or browser
  -> WebRTC room or native video session
  -> openCloser video transport adapter
  -> Pipecat or realtime model runtime
  -> persona module and tools
  -> realtime model audio output
  -> avatar renderer
  -> synchronized audio/video track back to the room
  -> openCloser session events, transcript, outcome, CRM write-back
```

The avatar renderer is not the business brain. It should receive audio and
optional expression/control hints. It should not own persona policy, clinical
logic, queue state, CRM updates, or final dispositions.

## Rendering Options

### Option 1: Managed Conversational Video Platform

Examples: Tavus CVI, D-ID Realtime Agents.

This is the fastest path to a polished photorealistic talking-head experience.
The vendor owns most of the video pipeline and provides a WebRTC-based
conversation experience. Tavus describes CVI as a real-time multimodal video
interface with Persona, Replica, and Conversation concepts, media over WebRTC
powered by Daily, and a configurable pipeline that includes perception,
turn-taking, STT, LLM, TTS, and realtime replica rendering.

Use this when the goal is a quick executive demo or a standalone video-agent
experiment.

Risks:

- It can duplicate openCloser's runtime, persona, STT, LLM, and TTS layers.
- It may reintroduce the latency path we are trying to avoid.
- Data retention, BAA/HIPAA, recording, likeness consent, and vendor subprocessor
  terms must be reviewed before healthcare use.
- The avatar vendor must not become the CRM control plane.

### Option 2: Avatar Provider as a Media Worker

Examples: LiveKit avatar plugins, Pipecat Tavus transport, Pipecat/Simli,
HeyGen Audio-to-Video, D-ID BYO audio/text.

This is the best fit for openCloser if we want realistic avatars while keeping
our own Interaction Core. The pattern is:

```text
openCloser runtime produces audio -> avatar provider renders video -> WebRTC room publishes avatar audio/video
```

LiveKit documents this model directly: an avatar provider joins the room as a
secondary participant, receives the agent session's audio output, generates
synchronized lip movement and gestures, and publishes audio/video tracks.
LiveKit also lists multiple avatar provider plugins and supports custom avatar
workers.

Pipecat is also aligned with this approach. Its Tavus transport lets a Pipecat
bot join a Daily room with a Tavus avatar and send audio for synchronized video
rendering. Simli's Pipecat guide shows `SimliVideoService` in the pipeline after
TTS, producing video output through Daily or WebRTC.

For a direct OpenAI Realtime path, the implementation detail is important:
instead of sending TTS output into the avatar, openCloser would tee or route the
realtime model's output audio into the avatar renderer. HeyGen's Audio-to-Video
API explicitly supports audio from speech-to-speech providers such as OpenAI
Realtime and streams video through WebRTC. Simli also accepts PCM audio and
returns talking-head video over WebRTC.

Use this for the first serious openCloser video spike.

Risks:

- Audio format and pacing matter. Most avatar renderers expect specific PCM
  sample rates and chunk sizes.
- Barge-in/interruption handling must stop both model audio and avatar playback.
- Mouth-sync and response latency need measured p50/p95 values, not vendor
  claims alone.
- Vendor avatar services may retain media or likeness data.

### Option 3: Browser-Rendered 2D or 3D Avatar

Examples: WebGL/Three.js VRM avatar, Ready Player Me-style avatar, Live2D/Rive,
Canvas/SVG face animation.

This is the lowest-vendor-risk option. The browser receives the model's audio
stream and renders a clearly synthetic avatar locally. Lip movement can start
with simple audio-energy mouth shapes and later move to phoneme or viseme
estimation.

Accurate lip sync is easier when the TTS engine emits viseme events. Azure
Speech, for example, supports `VisemeReceived` events and blend-shape style
output. With OpenAI Realtime audio output, we would likely need audio analysis,
phoneme estimation, or a secondary transcript/alignment path because the model
does not directly provide avatar animation curves.

Use this when privacy, cost, or clear synthetic presentation matters more than
photorealism.

Risks:

- Less lifelike than managed avatar providers.
- More client engineering.
- Lip sync may be approximate unless we introduce a TTS or alignment source
  that emits visemes.

### Option 4: Self-Hosted Neural Talking Head Renderer

Examples: research systems and open-source talking-head/lip-sync models.

This gives the most control but is not the first practical path. Real-time
photorealistic talking-head rendering is GPU-heavy, sensitive to model/license
terms, and operationally more complex than the rest of the MVP.

Use this only as R&D after a vendor-backed or browser-rendered video spike
proves product value.

Risks:

- GPU hosting and scaling cost.
- Harder p95 latency and session stability.
- Model licensing and likeness-rights review.
- More quality-control work for healthcare-facing use.

## Recommended Spike

Create a post-MVP spike with two tracks:

### Track A: Managed Avatar Worker

- Use LiveKit or Daily as the WebRTC room.
- Use Pipecat or a thin runtime adapter to connect the room to OpenAI Realtime.
- Feed the realtime model's output audio into one avatar provider.
- Test Simli, HeyGen Audio-to-Video, or Tavus first because they document audio
  to avatar/video patterns compatible with Pipecat, LiveKit, or realtime audio
  orchestration.
- Store only normalized openCloser events, transcript pointers, latency metrics,
  and final outcomes.

### Track B: Synthetic Browser Avatar

- Use a simple 2D or 3D avatar in the browser.
- Drive mouth movement from the model output audio stream.
- Keep it clearly synthetic.
- Compare user trust, latency, cost, and compliance posture against Track A.

## Evaluation Metrics

Measure both tracks with the same harness:

- room join latency
- time from user stop-speaking to first avatar audio
- time from user stop-speaking to first visible mouth movement
- audio/video sync offset
- interruption and barge-in recovery time
- 10-minute and 30-minute session stability
- CPU/GPU use on client and server
- vendor cost per minute and concurrency limits
- transcript and recording retention controls
- ability to preserve openCloser correlation IDs
- whether the provider can support healthcare privacy requirements

## Policy Questions Before Clinical Use

- Should a doctor avatar be photorealistic, stylized, or explicitly synthetic?
- What consent is required to use a clinician likeness?
- Must the avatar disclose that it is AI at call start and after interruptions?
- Can the avatar express uncertainty without implying clinical judgment?
- Which sessions may include video recording, transcript, summary only, or no
  persistent media?
- Which vendors can sign appropriate healthcare data-processing terms?
- What emergency and escalation behavior is required before any patient-facing
  video persona?

## Source Notes

- OpenAI `gpt-realtime` model docs: realtime text/audio input and output over
  WebRTC, WebSocket, or SIP; image input is supported, but output is text/audio,
  not video. <https://developers.openai.com/api/docs/models/gpt-realtime>
- LiveKit video and avatar docs: video input can be sampled or sent to supported
  realtime models; avatar output is a separate provider/worker that publishes
  synchronized audio/video tracks. <https://docs.livekit.io/agents/multimodality/vision/video/>
- LiveKit avatar provider overview: supported avatar plugins and custom avatar
  workers. <https://docs.livekit.io/agents/models/avatar/>
- Pipecat Tavus transport docs: Pipecat bot joins a Daily room with a Tavus
  avatar and sends audio for synchronized video rendering.
  <https://docs.pipecat.ai/api-reference/server/services/transport/tavus>
- Tavus CVI docs: real-time multimodal video interface, WebRTC/Daily, persona,
  replica, and configurable layers. <https://docs.tavus.io/sections/conversational-video-interface/overview-cvi>
- HeyGen Audio-to-Video API docs: accepts audio from voice orchestration stacks
  including Pipecat and OpenAI Realtime and streams avatar video to WebRTC.
  <https://docs.heygen.com/reference/audio-to-video-api>
- Simli WebRTC docs: accepts PCM audio and returns low-latency talking-head
  video over WebRTC. <https://docs.simli.com/api-reference/simli-webrtc>
- D-ID Realtime overview: realtime avatar agents streamed via WebRTC; can also
  receive external audio or text chunks. <https://docs.d-id.com/docs/realtime-overview>
- Azure Speech viseme docs: Speech SDK can emit viseme events for synthesized
  speech, useful for browser-rendered avatars. <https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-speech-synthesis-viseme>

