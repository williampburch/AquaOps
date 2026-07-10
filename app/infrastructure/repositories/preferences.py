from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.preferences import DEFAULT_PREFERENCES, UserPreferences, normalize_preferences
from app.infrastructure.db.models import UserPreferenceModel


class SqlAlchemyUserPreferenceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_for_user(self, user_id: int) -> UserPreferences:
        model = self.session.execute(
            select(UserPreferenceModel).where(UserPreferenceModel.user_id == user_id)
        ).scalar_one_or_none()
        if model is None:
            return DEFAULT_PREFERENCES
        return _preferences_from_model(model)

    def save_for_user(self, user_id: int, preferences: UserPreferences) -> UserPreferences:
        normalized = normalize_preferences(preferences)
        model = self.session.execute(
            select(UserPreferenceModel).where(UserPreferenceModel.user_id == user_id)
        ).scalar_one_or_none()
        if model is None:
            model = UserPreferenceModel(user_id=user_id)
            self.session.add(model)

        model.unit_system = normalized.unit_system
        model.volume_unit = normalized.volume_unit
        model.temperature_unit = normalized.temperature_unit
        model.date_format = normalized.date_format
        model.dashboard_density = normalized.dashboard_density
        model.advanced_mode = normalized.advanced_mode
        model.reminder_window_days = normalized.reminder_window_days
        model.enable_livestock = normalized.enable_livestock
        model.enable_plants = normalized.enable_plants
        model.enable_reports = normalized.enable_reports
        model.enable_notifications = normalized.enable_notifications
        model.enable_advanced_water = normalized.enable_advanced_water
        model.plant_care_mode = normalized.plant_care_mode

        self.session.commit()
        return _preferences_from_model(model)


def _preferences_from_model(model: UserPreferenceModel) -> UserPreferences:
    return normalize_preferences(
        UserPreferences(
            unit_system=model.unit_system,
            volume_unit=model.volume_unit,
            temperature_unit=model.temperature_unit,
            date_format=model.date_format,
            dashboard_density=model.dashboard_density,
            advanced_mode=model.advanced_mode,
            reminder_window_days=model.reminder_window_days,
            enable_livestock=model.enable_livestock,
            enable_plants=model.enable_plants,
            enable_reports=model.enable_reports,
            enable_notifications=model.enable_notifications,
            enable_advanced_water=model.enable_advanced_water,
            plant_care_mode=model.plant_care_mode,
        )
    )
