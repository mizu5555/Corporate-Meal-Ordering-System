"""Employee identity dependencies for employee-facing ordering APIs."""
from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, Request

from backend.core.errors import CodedHTTPException
from backend.core.security import decode_access_token


def _db_active_check(employee_id: int) -> None:
    """Reject the request if the employee account is inactive in the database."""
    from backend.db.connection import get_connection

    with get_connection() as conn:
        row = conn.execute(
            "SELECT is_active FROM users WHERE id = %s", (employee_id,)
        ).fetchone()
    if not row or not row["is_active"]:
        raise CodedHTTPException(
            status_code=403,
            code="account_disabled",
            detail="This account has been disabled",
        )


def get_employee_active_check() -> Callable[[int], None]:
    """Injectable that returns the active-status checker.

    Override via ``app.dependency_overrides`` in unit tests to avoid a live DB
    connection while still exercising the route logic.
    """
    return _db_active_check


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
    active_check: Annotated[Callable[[int], None], Depends(get_employee_active_check)] = ...,  # type: ignore[assignment]
) -> int:
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        payload = decode_access_token(auth[7:])
        if payload:
            if payload.get("role") != "employee":
                raise CodedHTTPException(status_code=403, code="forbidden", detail="employee role required")
            employee_id = int(payload["sub"])
            active_check(employee_id)
            return employee_id

    # Header fallback (tests / mock login)
    if x_user_role != "employee":
        raise CodedHTTPException(status_code=403, code="forbidden", detail="employee role required")
    if x_user_id is None:
        raise CodedHTTPException(status_code=400, code="validation_error", detail="x-user-id header missing")
    try:
        employee_id = int(x_user_id)
    except ValueError as exc:
        raise CodedHTTPException(status_code=400, code="validation_error", detail="x-user-id must be integer") from exc
    active_check(employee_id)
    return employee_id
