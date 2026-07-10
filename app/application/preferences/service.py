from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.preferences import UserPreferenceRepository
from app.domain.preferences import UserPreferences, normalize_preferences


@dataclass(frozen=True)
class UserPreferenceService:
    repository: UserPreferenceRepository

    def get_preferences(self, user_id: int) -> UserPreferences:
        return self.repository.get_for_user(user_id)

    def save_preferences(self, user_id: int, preferences: UserPreferences) -> UserPreferences:
        return self.repository.save_for_user(user_id, normalize_preferences(preferences))
