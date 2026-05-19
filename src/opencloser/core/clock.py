"""Clock protocol — single source of timestamps per FR-014.

All times are ISO 8601 in UTC with millisecond precision: 2026-05-19T17:00:00.000Z.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    """Abstraction so tests can inject a frozen clock."""

    def now_utc_ms(self) -> str:  # pragma: no cover - protocol
        ...

    def now_local(self, tz_name: str) -> datetime:  # pragma: no cover - protocol
        ...


class SystemClock:
    """Production clock backed by the OS time."""

    def now_utc_ms(self) -> str:
        return _format_utc_ms(datetime.now(UTC))

    def now_local(self, tz_name: str) -> datetime:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo(tz_name))


class FrozenClock:
    """Test clock — emits a fixed UTC instant and resolves local time via zoneinfo."""

    def __init__(self, fixed_utc: datetime) -> None:
        if fixed_utc.tzinfo is None:
            fixed_utc = fixed_utc.replace(tzinfo=UTC)
        self._fixed_utc = fixed_utc.astimezone(UTC)

    def now_utc_ms(self) -> str:
        return _format_utc_ms(self._fixed_utc)

    def now_local(self, tz_name: str) -> datetime:
        from zoneinfo import ZoneInfo

        return self._fixed_utc.astimezone(ZoneInfo(tz_name))


def _format_utc_ms(dt: datetime) -> str:
    """Format a UTC datetime as `YYYY-MM-DDTHH:MM:SS.sssZ`."""
    dt_utc = dt.astimezone(UTC)
    # Python's isoformat with timespec='milliseconds' includes the +00:00 offset; we want trailing Z.
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt_utc.microsecond // 1000:03d}Z"
