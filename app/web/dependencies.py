from __future__ import annotations

from collections.abc import Generator
from datetime import timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import generate_session_token, hash_session_token
from app.core.time import utc_now
from app.infrastructure.db.models import SessionModel, UserModel
from app.infrastructure.db.session import get_session


def get_db() -> Generator[Session]:
    yield from get_session()


DbSession = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_current_user(
    request: Request,
    db: DbSession,
    settings: SettingsDep,
) -> UserModel | None:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        return None

    token_hash = hash_session_token(token, settings.secret_key)
    statement = (
        select(SessionModel)
        .where(
            SessionModel.token_hash == token_hash,
            SessionModel.expires_at > utc_now(),
            SessionModel.revoked_at.is_(None),
        )
        .limit(1)
    )
    session_record = db.execute(statement).scalar_one_or_none()
    if session_record is None or not session_record.user.is_active:
        return None
    return session_record.user


CurrentUser = Annotated[UserModel | None, Depends(get_current_user)]


def create_login_session(user: UserModel, db: Session, settings: Settings) -> str:
    token = generate_session_token()
    db.add(
        SessionModel(
            user_id=user.id,
            token_hash=hash_session_token(token, settings.secret_key),
            expires_at=utc_now() + timedelta(days=settings.session_ttl_days),
        )
    )
    db.commit()
    return token


def require_current_user(current_user: CurrentUser) -> UserModel:
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )
    return current_user


AuthenticatedUser = Annotated[UserModel, Depends(require_current_user)]
