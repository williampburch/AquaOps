from __future__ import annotations

from datetime import UTC, datetime

UTC = UTC


def utc_now() -> datetime:
    return datetime.now(UTC)
