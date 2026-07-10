from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.notifications import (
    NotificationReadRepository,
    NotificationSnapshot,
)


@dataclass(frozen=True)
class NotificationService:
    repository: NotificationReadRepository

    def get_notifications(
        self,
        user_id: int,
        window_days: int = 14,
        plant_care_mode: str = "auto",
    ) -> NotificationSnapshot:
        return self.repository.get_snapshot(user_id, window_days, plant_care_mode)

    def complete_reminder(self, user_id: int, reminder_id: int) -> bool:
        return self.repository.complete_reminder(user_id, reminder_id)

    def snooze_reminder(self, user_id: int, reminder_id: int, days: int = 1) -> bool:
        if days < 1 or days > 30:
            raise ValueError("Snooze days must be between 1 and 30")
        return self.repository.snooze_reminder(user_id, reminder_id, days)
