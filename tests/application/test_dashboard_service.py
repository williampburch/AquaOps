from __future__ import annotations

from app.application.dashboard.service import DashboardService
from app.application.ports.dashboard import DashboardSnapshot


class FakeDashboardRepository:
    def __init__(self) -> None:
        self.seen_user_id: int | None = None

    def get_snapshot(self, user_id: int | None) -> DashboardSnapshot:
        self.seen_user_id = user_id
        return DashboardSnapshot(
            tank_count=1,
            event_count=2,
            livestock_count=3,
            plant_count=4,
            recent_events=[],
            upcoming_reminders=[],
            latest_measurements=[],
        )


def test_dashboard_service_delegates_to_repository() -> None:
    repository = FakeDashboardRepository()
    service = DashboardService(repository)

    snapshot = service.get_dashboard(user_id=42)

    assert repository.seen_user_id == 42
    assert snapshot.tank_count == 1
    assert snapshot.event_count == 2
