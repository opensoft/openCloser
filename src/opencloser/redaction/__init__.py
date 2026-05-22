"""Transcript redaction boundary — Slice 2.

The RedactionLayer transforms transcript text before any transcript artifact is
written to disk (spec FR-028–FR-030). Default-on; configurable via the
``[redaction]`` section of config/slice2.toml.

See specs/002-mock-call-real-crm/contracts/redaction-layer.md.
"""

from __future__ import annotations
