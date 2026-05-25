"""Employee identity dependencies for employee-facing ordering APIs."""
from __future__ import annotations

from typing import Annotated

from fastapi import Header, Request

from backend.core.errors import CodedHTTPException
from backend.core.security import decode_access_token


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
    x_user_role: Annotated[str | None, Header()] = None,
    x_user_id: Annotated[str | None, Header()] = None,
) -> int:
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        payload = decode_access_token(auth[7:])
        if payload:
            if payload.get("role") != "employee":
                raise CodedHTTPException(status_code=403, code="forbidden", detail="employee role required")
            return int(payload["sub"])

    # Header fallback (tests / mock login)
    if x_user_role != "employee":
        raise CodedHTTPException(status_code=403, code="forbidden", detail="employee role required")
    if x_user_id is None:
        raise CodedHTTPException(status_code=400, code="validation_error", detail="x-user-id header missing")
    try:
        return int(x_user_id)
    except ValueError as exc:
        raise CodedHTTPException(status_code=400, code="validation_error", detail="x-user-id must be integer") from exc
