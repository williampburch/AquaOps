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
