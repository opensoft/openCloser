"""Transcript redaction boundary — Slice 2.

This package is a **boundary scaffold only** in the foundation PR — it carries the
import-time contract (`tests/test_imports.py`) and the package docstring, but the
RedactionLayer implementation lands in the US6 sub-PR (#4). The eventual layer
will transform transcript text before any transcript artifact is written to disk
(spec FR-028, FR-029, FR-030); default-on; configurable via the ``[redaction]``
section of config/slice2.toml.

See specs/002-mock-call-real-crm/contracts/redaction-layer.md.
"""

from __future__ import annotations
