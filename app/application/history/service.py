from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.history import CareHistoryReadRepository
from app.domain.enums import EventType, MaintenanceType

CARE_HISTORY_FILTERS: tuple[tuple[str, str], ...] = (
    ("all", "All"),
    ("water_tests", "Water tests"),
    ("maintenance", "Maintenance"),
    ("feeding", "Feeding"),
    ("dosing", "Dosing"),
    ("inventory", "Livestock & plants"),
    ("observations", "Observations"),
    ("photos", "Photos"),
    ("problems", "Problems"),
)

_EVENT_TYPES_BY_FILTER: dict[str, tuple[str, ...] | None] = {
    "all": None,
    "water_tests": (EventType.WATER_TEST.value,),
    "maintenance": (EventType.MAINTENANCE.value,),
    "feeding": (EventType.FEEDING.value,),
    "dosing": (EventType.FERTILIZER.value,),
    "inventory": (EventType.LIVESTOCK_CHANGE.value, EventType.PLANT_CHANGE.value),
    "observations": (EventType.NOTE.value,),
    "photos": (EventType.PHOTO.value,),
    "problems": (EventType.PROBLEM_CHANGE.value,),
}

MAINTENANCE_TASK_FILTERS: tuple[tuple[str, str], ...] = tuple(
    (item.value, item.value.replace("_", " ").title()) for item in MaintenanceType
)


@dataclass(frozen=True)
class CareHistoryService:
    repository: CareHistoryReadRepository

    def list_tank_history(
        self,
        user_id: int,
        tank_id: int,
        *,
        category: str = "all",
        maintenance_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
        plant_care_mode: str = "auto",
    ):
        normalized_category = category if category in _EVENT_TYPES_BY_FILTER else "all"
        valid_tasks = {value for value, _ in MAINTENANCE_TASK_FILTERS}
        normalized_task = (
            maintenance_type
            if normalized_category == "maintenance" and maintenance_type in valid_tasks
            else None
        )
        return self.repository.list_tank_history(
            user_id,
            tank_id,
            event_types=_EVENT_TYPES_BY_FILTER[normalized_category],
            maintenance_type=normalized_task,
            page=max(page, 1),
            page_size=max(1, min(page_size, 50)),
            plant_care_mode=plant_care_mode,
        )

    @staticmethod
    def normalize_filters(category: str, maintenance_type: str | None) -> tuple[str, str | None]:
        normalized_category = category if category in _EVENT_TYPES_BY_FILTER else "all"
        valid_tasks = {value for value, _ in MAINTENANCE_TASK_FILTERS}
        normalized_task = (
            maintenance_type
            if normalized_category == "maintenance" and maintenance_type in valid_tasks
            else None
        )
        return normalized_category, normalized_task
