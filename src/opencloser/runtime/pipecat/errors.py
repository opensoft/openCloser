"""Slice 3 Pipecat runtime exception hierarchy (FR-013 + Round 1 Q4).

The three live-runtime degradation triggers that the orchestrator translates
into either ``failed`` (pre-connected) or ``needs_human_review``/
``script_truncated`` (post-connected) per ``contracts/pipecat-runtime.md``
Required Behavior #5.

Stub module — bodies land in T030 / T064. Per T013 Q5 the contract test
(T014) expects these types to exist now so it can ``pytest.raises(...)`` on
them; the live runtime that emits them lands later.
"""

from __future__ import annotations


class RealtimeProviderError(Exception):
    """Provider-side failure from the configured real-time AI model provider
    (FR-013 Round 1 Q4 (a)). Pre-connected → ``failed``; post-connected →
    ``needs_human_review`` / ``script_truncated``.

    Carries ``transient: bool`` (Round 4 R4-Q5). A transient PRE-connection
    provider error is retried within the connect budget (it is NOT immediately
    a degradation trigger); a terminal pre-connection error finalizes per
    FR-013. POST-connection, ANY ``RealtimeProviderError`` is a degradation
    trigger regardless of ``transient``. Defaults to terminal
    (``transient=False``) so a bare ``RealtimeProviderError(message)`` — as the
    contract-test fakes raise — is treated as a terminal failure.
    """

    def __init__(self, *args: object, transient: bool = False) -> None:
        super().__init__(*args)
        self.transient = transient


class PipecatRuntimeError(Exception):
    """Pipecat runtime crash or unrecoverable adapter failure
    (FR-013 Round 1 Q4 (b)). Same disposition mapping as
    ``RealtimeProviderError``."""


class SilenceAfterConnectionTimeout(Exception):
    """The deployment-configurable silence-after-connection /
    no-extraction-event timeout elapsed (FR-013 Round 1 Q4 (c)).

    By construction this can ONLY fire after the call reached ``connected``
    (the silence timer starts on connection), so the disposition is always
    ``needs_human_review`` / ``script_truncated``.
    """

    def __init__(self, session_id: str, timeout_sec: int) -> None:
        self.session_id = session_id
        self.timeout_sec = timeout_sec
        super().__init__(
            f"silence-after-connection timeout: session={session_id} after {timeout_sec}s"
        )
