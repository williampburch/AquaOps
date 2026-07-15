from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.application.ports.problems import ProblemCreate
from app.core.security import hash_password
from app.core.time import utc_now
from app.infrastructure.db import models  # noqa: F401
from app.infrastructure.db.base import Base
from app.infrastructure.db.models import EventModel, TankModel, UserModel
from app.infrastructure.repositories.problems import SqlAlchemyProblemRepository


@pytest.fixture
def session() -> Generator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    with testing_session() as db_session:
        yield db_session

    Base.metadata.drop_all(bind=engine)


def test_problem_repository_keeps_records_and_links_inside_the_owned_tank(
    session: Session,
) -> None:
    owner = UserModel(
        email="owner@example.com",
        username="owner",
        password_hash=hash_password("a-long-test-password"),
    )
    other_user = UserModel(
        email="other@example.com",
        username="other",
        password_hash=hash_password("a-long-test-password"),
    )
    tank = TankModel(user=owner, name="Display Tank", tank_type="planted")
    other_tank = TankModel(user=other_user, name="Other Tank", tank_type="freshwater")
    owned_event = EventModel(
        user=owner,
        tank=tank,
        event_type="note",
        title="Fish hiding",
        occurred_at=utc_now(),
    )
    foreign_event = EventModel(
        user=other_user,
        tank=other_tank,
        event_type="note",
        title="Private observation",
        occurred_at=utc_now(),
    )
    session.add_all([owner, other_user, tank, other_tank, owned_event, foreign_event])
    session.commit()

    repository = SqlAlchemyProblemRepository(session)
    problem_id = repository.create_problem(
        owner.id,
        ProblemCreate(
            tank_id=tank.id,
            problem_type="illness",
            title="Tetras acting stressed",
            description="Several fish are hiding.",
            severity="high",
            started_at=utc_now(),
            event_ids=(owned_event.id, foreign_event.id),
        ),
    )

    assert problem_id is not None
    detail = repository.get_problem(owner.id, problem_id)
    assert detail is not None
    assert {event.title for event in detail.linked_events} == {
        "Fish hiding",
        "Problem opened: Tetras acting stressed",
    }
    opened_event = next(
        event for event in detail.linked_events if event.event_type == "problem_change"
    )
    assert not repository.unlink_event(owner.id, problem_id, opened_event.id)
    assert repository.get_problem(other_user.id, problem_id) is None
    assert repository.list_problems(other_user.id) == []
    assert not repository.update_status(other_user.id, problem_id, "resolved", None)

    assert repository.update_status(
        owner.id,
        problem_id,
        "resolved",
        "Improved aeration.",
    )
    resolved = repository.get_problem(owner.id, problem_id)
    assert resolved is not None
    assert resolved.problem.status == "resolved"
    assert resolved.problem.resolution_notes == "Improved aeration."
    assert "Problem resolved: Tetras acting stressed" in {
        event.title for event in resolved.linked_events
    }
