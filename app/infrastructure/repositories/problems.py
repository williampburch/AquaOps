from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.application.ports.problems import (
    ProblemCreate,
    ProblemDetail,
    ProblemEvent,
    ProblemRecord,
)
from app.core.time import utc_now
from app.domain.enums import EventType
from app.infrastructure.db.models import (
    EventModel,
    PhotoEventDetailModel,
    ProblemEventLinkModel,
    ProblemModel,
    TankModel,
)


class SqlAlchemyProblemRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_problems(self, user_id: int) -> list[ProblemRecord]:
        statement = (
            select(ProblemModel, TankModel.name, func.count(ProblemEventLinkModel.id))
            .join(TankModel, TankModel.id == ProblemModel.tank_id)
            .outerjoin(ProblemEventLinkModel, ProblemEventLinkModel.problem_id == ProblemModel.id)
            .where(ProblemModel.user_id == user_id)
            .group_by(ProblemModel.id, TankModel.name)
            .order_by(
                (ProblemModel.status == "resolved").asc(),
                ProblemModel.started_at.desc(),
            )
        )
        return [
            _problem_record(problem, tank_name, linked_count)
            for problem, tank_name, linked_count in self.session.execute(statement).all()
        ]

    def create_problem(self, user_id: int, data: ProblemCreate) -> int | None:
        tank = self.session.scalar(
            select(TankModel).where(
                TankModel.id == data.tank_id,
                TankModel.user_id == user_id,
                TankModel.archived_at.is_(None),
            )
        )
        if tank is None:
            return None
        problem = ProblemModel(
            user_id=user_id,
            tank_id=tank.id,
            problem_type=data.problem_type,
            title=data.title.strip(),
            description=(data.description or "").strip() or None,
            severity=data.severity,
            status="open",
            started_at=data.started_at,
            resolved_at=None,
            resolution_notes=None,
        )
        self.session.add(problem)
        self.session.flush()
        opened_event = EventModel(
            user_id=user_id,
            tank_id=tank.id,
            event_type=EventType.PROBLEM_CHANGE.value,
            title=f"Problem opened: {problem.title}",
            notes=problem.description or "",
            occurred_at=problem.started_at,
            metadata_json={
                "problem_id": problem.id,
                "problem_type": problem.problem_type,
                "severity": problem.severity,
                "status": problem.status,
            },
        )
        self.session.add(opened_event)
        self.session.flush()
        self._link_valid_events(problem, (*data.event_ids, opened_event.id))
        self.session.commit()
        return problem.id

    def get_problem(self, user_id: int, problem_id: int) -> ProblemDetail | None:
        row = self.session.execute(
            select(ProblemModel, TankModel.name)
            .join(TankModel, TankModel.id == ProblemModel.tank_id)
            .where(ProblemModel.id == problem_id, ProblemModel.user_id == user_id)
        ).one_or_none()
        if row is None:
            return None
        problem, tank_name = row
        linked = self._linked_events(problem.id)
        linked_ids = {event.id for event in linked}
        context = [
            event
            for event in self.list_tank_context(user_id, problem.tank_id, problem.started_at, 50)
            if event.id not in linked_ids
        ]
        return ProblemDetail(
            problem=_problem_record(problem, tank_name, len(linked)),
            linked_events=linked,
            context_events=context,
        )

    def list_tank_context(
        self,
        user_id: int,
        tank_id: int,
        started_at: datetime,
        limit: int = 30,
    ) -> list[ProblemEvent]:
        statement = (
            select(EventModel, PhotoEventDetailModel.media_asset_id, PhotoEventDetailModel.caption)
            .outerjoin(PhotoEventDetailModel, PhotoEventDetailModel.event_id == EventModel.id)
            .where(
                EventModel.user_id == user_id,
                EventModel.tank_id == tank_id,
                EventModel.occurred_at >= started_at - timedelta(days=30),
                EventModel.occurred_at <= utc_now(),
            )
            .order_by(EventModel.occurred_at.desc(), EventModel.id.desc())
            .limit(limit)
        )
        return [
            _problem_event(event, media_asset_id, caption)
            for event, media_asset_id, caption in self.session.execute(statement).all()
        ]

    def update_status(
        self,
        user_id: int,
        problem_id: int,
        status: str,
        resolution_notes: str | None,
    ) -> bool:
        problem = self._owned_problem(user_id, problem_id)
        if problem is None:
            return False
        problem.status = status
        problem.resolution_notes = (resolution_notes or "").strip() or None
        problem.resolved_at = utc_now() if status == "resolved" else None
        status_event = EventModel(
            user_id=user_id,
            tank_id=problem.tank_id,
            event_type=EventType.PROBLEM_CHANGE.value,
            title=f"Problem {status}: {problem.title}",
            notes=problem.resolution_notes or "",
            occurred_at=utc_now(),
            metadata_json={
                "problem_id": problem.id,
                "problem_type": problem.problem_type,
                "severity": problem.severity,
                "status": status,
            },
        )
        self.session.add(status_event)
        self.session.flush()
        self._link_valid_events(problem, (status_event.id,))
        self.session.commit()
        return True

    def link_events(self, user_id: int, problem_id: int, event_ids: tuple[int, ...]) -> bool:
        problem = self._owned_problem(user_id, problem_id)
        if problem is None:
            return False
        self._link_valid_events(problem, event_ids)
        self.session.commit()
        return True

    def unlink_event(self, user_id: int, problem_id: int, event_id: int) -> bool:
        problem = self._owned_problem(user_id, problem_id)
        if problem is None:
            return False
        event = self.session.scalar(
            select(EventModel).where(
                EventModel.id == event_id,
                EventModel.user_id == user_id,
                EventModel.tank_id == problem.tank_id,
            )
        )
        if event is None or event.event_type == EventType.PROBLEM_CHANGE.value:
            return False
        result = self.session.execute(
            delete(ProblemEventLinkModel).where(
                ProblemEventLinkModel.problem_id == problem.id,
                ProblemEventLinkModel.event_id == event_id,
            )
        )
        self.session.commit()
        return bool(result.rowcount)

    def _owned_problem(self, user_id: int, problem_id: int) -> ProblemModel | None:
        return self.session.scalar(
            select(ProblemModel).where(
                ProblemModel.id == problem_id,
                ProblemModel.user_id == user_id,
            )
        )

    def _link_valid_events(self, problem: ProblemModel, event_ids: tuple[int, ...]) -> None:
        unique_ids = tuple(dict.fromkeys(event_ids))
        if not unique_ids:
            return
        valid_ids = self.session.scalars(
            select(EventModel.id).where(
                EventModel.id.in_(unique_ids),
                EventModel.user_id == problem.user_id,
                EventModel.tank_id == problem.tank_id,
            )
        ).all()
        existing_ids = set(
            self.session.scalars(
                select(ProblemEventLinkModel.event_id).where(
                    ProblemEventLinkModel.problem_id == problem.id,
                    ProblemEventLinkModel.event_id.in_(valid_ids),
                )
            ).all()
        )
        self.session.add_all(
            ProblemEventLinkModel(problem_id=problem.id, event_id=event_id)
            for event_id in valid_ids
            if event_id not in existing_ids
        )

    def _linked_events(self, problem_id: int) -> list[ProblemEvent]:
        statement = (
            select(EventModel, PhotoEventDetailModel.media_asset_id, PhotoEventDetailModel.caption)
            .join(ProblemEventLinkModel, ProblemEventLinkModel.event_id == EventModel.id)
            .outerjoin(PhotoEventDetailModel, PhotoEventDetailModel.event_id == EventModel.id)
            .where(ProblemEventLinkModel.problem_id == problem_id)
            .order_by(EventModel.occurred_at.desc(), EventModel.id.desc())
        )
        return [
            _problem_event(event, media_asset_id, caption)
            for event, media_asset_id, caption in self.session.execute(statement).all()
        ]


def _problem_record(
    problem: ProblemModel,
    tank_name: str,
    linked_event_count: int,
) -> ProblemRecord:
    return ProblemRecord(
        id=problem.id,
        tank_id=problem.tank_id,
        tank_name=tank_name,
        problem_type=problem.problem_type,
        title=problem.title,
        description=problem.description,
        severity=problem.severity,
        status=problem.status,
        started_at=problem.started_at,
        resolved_at=problem.resolved_at,
        resolution_notes=problem.resolution_notes,
        linked_event_count=linked_event_count,
    )


def _problem_event(
    event: EventModel,
    media_asset_id: int | None,
    photo_caption: str | None,
) -> ProblemEvent:
    return ProblemEvent(
        id=event.id,
        event_type=event.event_type,
        title=event.title,
        notes=event.notes,
        occurred_at=event.occurred_at,
        media_asset_id=media_asset_id,
        photo_caption=photo_caption,
    )
