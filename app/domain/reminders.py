from __future__ import annotations

from datetime import datetime, timedelta

from app.domain.enums import FertilizerProductKey

DEFAULT_FERTILIZER_INTERVAL_DAYS: dict[str, int] = {
    FertilizerProductKey.SEACHEM_FLOURISH.value: 7,
    FertilizerProductKey.ROOT_TABS.value: 90,
    FertilizerProductKey.EASY_GREEN.value: 7,
}


def calculate_next_due_at(
    occurred_at: datetime,
    product_key: str,
    interval_days_override: int | None = None,
) -> datetime | None:
    if interval_days_override is not None:
        if interval_days_override <= 0:
            raise ValueError("interval_days_override must be greater than zero")
        return occurred_at + timedelta(days=interval_days_override)

    interval_days = DEFAULT_FERTILIZER_INTERVAL_DAYS.get(product_key)
    if interval_days is None:
        return None
    return occurred_at + timedelta(days=interval_days)
