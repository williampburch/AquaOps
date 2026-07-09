from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Optional


@dataclass(frozen=True)
class NotificationItem:
    id: int
    title: str
    reminder_type: str
    due_at: datetime
    tank_name: Optional[str]
    status: str


@dataclass(frozen=True)
class NotificationSnapshot:
    overdue_count: int
    due_today_count: int
    upcoming_count: int
    items: list[NotificationItem]


class NotificationReadRepository(Protocol):
    def get_snapshot(self, user_id: int) -> NotificationSnapshot:
        """Return open reminders and alert-style notifications for a user."""
