from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.care_plans import CarePlanRepository, CareScheduleUpdate
from app.domain.care_plans import CARE_TASKS
from app.domain.care_profiles import CARE_PROFILES


@dataclass(frozen=True)
class CarePlanService:
    repository: CarePlanRepository

    def get_care_plan(self, user_id: int, tank_id: int):
        return self.repository.get_care_plan(user_id, tank_id)

    def apply_profile(
        self,
        user_id: int,
        tank_id: int,
        profile_key: str,
        strategy: str,
        *,
        confirmed: bool = False,
    ) -> bool:
        profile = CARE_PROFILES.get(profile_key)
        if profile is None or profile.advanced or profile_key == "custom":
            raise ValueError("Choose an available care profile")
        if strategy not in {"merge", "replace_profile", "start_over"}:
            raise ValueError("Choose how AquaOps should apply this profile")
        if strategy == "start_over" and not confirmed:
            raise ValueError("Confirm that you want to disable the current plan and start fresh")
        return self.repository.apply_profile(user_id, tank_id, profile_key, strategy)

    def save_advanced_plan(
        self,
        user_id: int,
        tank_id: int,
        schedules: list[CareScheduleUpdate],
    ) -> bool:
        for schedule in schedules:
            if schedule.config_type != "custom" and schedule.config_type not in CARE_TASKS:
                raise ValueError("A care task is not supported")
            self._validate_schedule(schedule)
        return self.repository.save_advanced_plan(user_id, tank_id, schedules)

    def add_custom_task(
        self,
        user_id: int,
        tank_id: int,
        schedule: CareScheduleUpdate,
    ) -> bool:
        if schedule.config_type != "custom":
            raise ValueError("Custom task type is required")
        if not (schedule.label or "").strip():
            raise ValueError("Custom task name is required")
        if len((schedule.label or "").strip()) > 160:
            raise ValueError("Custom task name must be 160 characters or fewer")
        self._validate_schedule(schedule)
        return self.repository.add_custom_task(user_id, tank_id, schedule)

    @staticmethod
    def _validate_schedule(schedule: CareScheduleUpdate) -> None:
        if schedule.schedule_mode not in {"scheduled", "as_needed"}:
            raise ValueError("Choose scheduled or as-needed care")
        if (
            schedule.enabled
            and schedule.schedule_mode == "scheduled"
            and (schedule.interval_days is None or not 1 <= schedule.interval_days <= 3650)
        ):
            raise ValueError("Scheduled care must repeat every 1 to 3650 days")
        if schedule.preferred_weekday is not None and not 0 <= schedule.preferred_weekday <= 6:
            raise ValueError("Choose a valid preferred weekday")
        if schedule.notes and len(schedule.notes) > 1000:
            raise ValueError("Care plan notes must be 1000 characters or fewer")
