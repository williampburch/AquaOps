from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.notifications import (
    NotificationReadRepository,
    NotificationSnapshot,
)


@dataclass(frozen=True, slots=True)
class NotificationService:
    repository: NotificationReadRepository

    def get_notifications(self, user_id: int) -> NotificationSnapshot:
        return self.repository.get_snapshot(user_id)
