from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class NotificationItem:
    id: int
    title: str
    reminder_type: str
    due_at: datetime
    tank_name: str | None
    status: str


@dataclass(frozen=True)
class NotificationSnapshot:
    overdue_count: int
    due_today_count: int
    upcoming_count: int
    items: list[NotificationItem]
    plant_care_active: bool = False


class NotificationReadRepository(Protocol):
    def get_snapshot(
        self,
        user_id: int,
        window_days: int = 14,
        plant_care_mode: str = "auto",
    ) -> NotificationSnapshot:
        """Return open reminders and alert-style notifications for a user."""
