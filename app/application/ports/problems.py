from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class ProblemCreate:
    tank_id: int
    problem_type: str
    title: str
    description: str | None
    severity: str
    started_at: datetime
    event_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class ProblemRecord:
    id: int
    tank_id: int
    tank_name: str
    problem_type: str
    title: str
    description: str | None
    severity: str
    status: str
    started_at: datetime
    resolved_at: datetime | None
    resolution_notes: str | None
    linked_event_count: int = 0


@dataclass(frozen=True)
class ProblemEvent:
    id: int
    event_type: str
    title: str
    notes: str | None
    occurred_at: datetime
    media_asset_id: int | None = None
    photo_caption: str | None = None


@dataclass(frozen=True)
class ProblemDetail:
    problem: ProblemRecord
    linked_events: list[ProblemEvent]
    context_events: list[ProblemEvent]


class ProblemRepository(Protocol):
    def list_problems(self, user_id: int) -> list[ProblemRecord]: ...

    def create_problem(self, user_id: int, data: ProblemCreate) -> int | None: ...

    def get_problem(self, user_id: int, problem_id: int) -> ProblemDetail | None: ...

    def list_tank_context(
        self,
        user_id: int,
        tank_id: int,
        started_at: datetime,
        limit: int = 30,
    ) -> list[ProblemEvent]: ...

    def update_status(
        self,
        user_id: int,
        problem_id: int,
        status: str,
        resolution_notes: str | None,
    ) -> bool: ...

    def link_events(self, user_id: int, problem_id: int, event_ids: tuple[int, ...]) -> bool: ...

    def unlink_event(self, user_id: int, problem_id: int, event_id: int) -> bool: ...
