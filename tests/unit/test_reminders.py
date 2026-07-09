from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.domain.enums import FertilizerProductKey
from app.domain.reminders import calculate_next_due_at


UTC = timezone.utc


def test_calculates_builtin_root_tab_due_date() -> None:
    occurred_at = datetime(2026, 7, 9, 12, 0, tzinfo=UTC)

    due_at = calculate_next_due_at(occurred_at, FertilizerProductKey.ROOT_TABS.value)

    assert due_at == datetime(2026, 10, 7, 12, 0, tzinfo=UTC)


def test_custom_fertilizer_without_interval_has_no_due_date() -> None:
    occurred_at = datetime(2026, 7, 9, 12, 0, tzinfo=UTC)

    due_at = calculate_next_due_at(occurred_at, FertilizerProductKey.CUSTOM.value)

    assert due_at is None


def test_interval_override_must_be_positive() -> None:
    occurred_at = datetime(2026, 7, 9, 12, 0, tzinfo=UTC)

    with pytest.raises(ValueError, match="greater than zero"):
        calculate_next_due_at(occurred_at, FertilizerProductKey.EASY_GREEN.value, 0)
