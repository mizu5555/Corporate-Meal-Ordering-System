"""Employee identity dependencies for employee-facing ordering APIs."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Request

from backend.core.config import settings
from backend.core.errors import CodedHTTPException
from backend.core.security import decode_access_token
from backend.core.user_directory import get_user_repository
from backend.repositories.user_repository import UserRepository


def _assert_active_employee(user_id: int, repo: UserRepository) -> None:
    user = repo.get_by_id(user_id)
    if user is None:
        if settings.database_url:
            raise CodedHTTPException(status_code=401, code="invalid_token", detail="employee account not found")
        return
    if user.role != "employee":
        raise CodedHTTPException(status_code=403, code="forbidden", detail="employee role required")
    if not user.is_active:
        raise CodedHTTPException(
            status_code=403,
            code="account_disabled",
            detail="This account has been disabled",
        )


def require_employee_role(
    request: Request,
    x_user_role: Annotated[str | None, Header()] = None,
) -> None:
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        payload = decode_access_token(auth[7:])
        if payload:
            if payload.get("role") != "employee":
                raise CodedHTTPException(status_code=403, code="forbidden", detail="employee role required")
            return

    if x_user_role != "employee":
        raise CodedHTTPException(status_code=403, code="forbidden", detail="employee role required")


def require_employee(
    request: Request,
    repo: Annotated[UserRepository, Depends(get_user_repository)],
    x_user_role: Annotated[str | None, Header()] = None,
    x_user_id: Annotated[str | None, Header()] = None,
) -> int:
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        payload = decode_access_token(auth[7:])
        if payload:
            if payload.get("role") != "employee":
                raise CodedHTTPException(status_code=403, code="forbidden", detail="employee role required")
            try:
                user_id = int(payload["sub"])
            except (KeyError, ValueError, TypeError) as exc:
                raise CodedHTTPException(status_code=401, code="invalid_token", detail="invalid token") from exc
            _assert_active_employee(user_id, repo)
            return user_id

    # Header fallback (tests / mock login)
    if x_user_role != "employee":
        raise CodedHTTPException(status_code=403, code="forbidden", detail="employee role required")
    if x_user_id is None:
        raise CodedHTTPException(status_code=400, code="validation_error", detail="x-user-id header missing")
    try:
        user_id = int(x_user_id)
    except ValueError as exc:
        raise CodedHTTPException(status_code=400, code="validation_error", detail="x-user-id must be integer") from exc
    _assert_active_employee(user_id, repo)
    return user_id
