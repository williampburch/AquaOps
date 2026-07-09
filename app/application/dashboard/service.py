from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.dashboard import DashboardReadRepository, DashboardSnapshot


@dataclass(frozen=True)
class DashboardService:
    repository: DashboardReadRepository

    def get_dashboard(self, user_id: int | None) -> DashboardSnapshot:
        return self.repository.get_snapshot(user_id)
