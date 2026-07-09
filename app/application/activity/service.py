from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.activity import ActivityReadRepository


@dataclass(frozen=True, slots=True)
class ActivityService:
    repository: ActivityReadRepository

    def list_recent_events(self, user_id: int):
        return self.repository.list_recent_events(user_id)

    def get_reports_snapshot(self, user_id: int):
        return self.repository.get_reports_snapshot(user_id)
