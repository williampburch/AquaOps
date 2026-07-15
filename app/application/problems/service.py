from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.problems import ProblemCreate, ProblemRepository
from app.domain.problems import (
    PROBLEM_SEVERITY_LABELS,
    PROBLEM_STATUS_LABELS,
    PROBLEM_TYPE_LABELS,
)


@dataclass(frozen=True)
class ProblemService:
    repository: ProblemRepository

    def list_problems(self, user_id: int):
        return self.repository.list_problems(user_id)

    def create_problem(self, user_id: int, data: ProblemCreate) -> int | None:
        if data.problem_type not in PROBLEM_TYPE_LABELS:
            raise ValueError("Choose a supported problem type")
        if data.severity not in PROBLEM_SEVERITY_LABELS:
            raise ValueError("Choose a severity")
        if not data.title.strip():
            raise ValueError("Problem title is required")
        if len(data.title.strip()) > 180:
            raise ValueError("Problem title must be 180 characters or fewer")
        return self.repository.create_problem(user_id, data)

    def get_problem(self, user_id: int, problem_id: int):
        return self.repository.get_problem(user_id, problem_id)

    def list_tank_context(self, user_id: int, tank_id: int, started_at, limit: int = 30):
        return self.repository.list_tank_context(user_id, tank_id, started_at, limit)

    def update_status(
        self,
        user_id: int,
        problem_id: int,
        status: str,
        resolution_notes: str | None,
    ) -> bool:
        if status not in PROBLEM_STATUS_LABELS:
            raise ValueError("Choose a valid problem status")
        return self.repository.update_status(user_id, problem_id, status, resolution_notes)

    def link_events(self, user_id: int, problem_id: int, event_ids: tuple[int, ...]) -> bool:
        return self.repository.link_events(user_id, problem_id, event_ids)

    def unlink_event(self, user_id: int, problem_id: int, event_id: int) -> bool:
        return self.repository.unlink_event(user_id, problem_id, event_id)
