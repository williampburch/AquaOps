from __future__ import annotations

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import hash_password, hash_session_token, verify_password
from app.core.time import utc_now
from app.infrastructure.db.models import SessionModel, UserModel
from app.web.dependencies import CurrentUser, create_login_session, get_db

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory=get_settings().templates_dir)

DbSession = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
FormText = Annotated[str, Form(...)]


@router.get("/register")
def register_form(request: Request, current_user: CurrentUser):
    if current_user:
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request,
        "auth/register.html",
        {
            "title": "Create account",
            "active_nav": "auth",
            "current_user": current_user,
            "error": None,
        },
    )


@router.post("/register")
def register(
    request: Request,
    username: FormText,
    email: FormText,
    password: FormText,
    db: DbSession,
    settings: SettingsDep,
):
    normalized_email = email.strip().lower()
    normalized_username = username.strip()
    existing_user = db.execute(
        select(UserModel).where(
            (UserModel.email == normalized_email) | (UserModel.username == normalized_username)
        )
    ).scalar_one_or_none()
    if existing_user:
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            {
                "title": "Create account",
                "active_nav": "auth",
                "current_user": None,
                "error": "That email or username is already in use.",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user = UserModel(
        email=normalized_email,
        username=normalized_username,
        password_hash=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_login_session(user, db, settings)
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    _set_session_cookie(response, token, settings)
    return response


@router.get("/login")
def login_form(request: Request, current_user: CurrentUser):
    if current_user:
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request,
        "auth/login.html",
        {
            "title": "Sign in",
            "active_nav": "auth",
            "current_user": current_user,
            "error": None,
        },
    )


@router.post("/login")
def login(
    request: Request,
    email: FormText,
    password: FormText,
    db: DbSession,
    settings: SettingsDep,
):
    user = db.execute(
        select(UserModel).where(
            UserModel.email == email.strip().lower(),
            UserModel.is_active.is_(True),
        )
    ).scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {
                "title": "Sign in",
                "active_nav": "auth",
                "current_user": None,
                "error": "Invalid email or password.",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    token = create_login_session(user, db, settings)
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    _set_session_cookie(response, token, settings)
    return response


@router.post("/logout")
def logout(
    request: Request,
    db: DbSession,
    settings: SettingsDep,
):
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        token_hash = hash_session_token(token, settings.secret_key)
        session_record = db.execute(
            select(SessionModel).where(SessionModel.token_hash == token_hash)
        ).scalar_one_or_none()
        if session_record:
            session_record.revoked_at = utc_now()
            db.commit()

    response = RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(settings.session_cookie_name)
    return response


def _set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=int(timedelta(days=settings.session_ttl_days).total_seconds()),
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
    )
