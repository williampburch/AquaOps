from __future__ import annotations

from typing import Protocol

from app.domain.preferences import UserPreferences


class UserPreferenceRepository(Protocol):
    def get_for_user(self, user_id: int) -> UserPreferences:
        """Return saved preferences for a user or defaults when no row exists."""

    def save_for_user(self, user_id: int, preferences: UserPreferences) -> UserPreferences:
        """Create or update preferences for a user."""
