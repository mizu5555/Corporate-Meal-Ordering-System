"""Employee identity dependencies for employee-facing ordering APIs."""
from __future__ import annotations

from typing import Annotated

from fastapi import Header

from backend.core.errors import CodedHTTPException


def require_employee_role(
    x_user_role: Annotated[str | None, Header()] = None,
) -> None:
    if x_user_role != "employee":
        raise CodedHTTPException(status_code=403, code="forbidden", detail="employee role required")


def require_employee(
    x_user_role: Annotated[str | None, Header()] = None,
    x_user_id: Annotated[str | None, Header()] = None,
) -> int:
    require_employee_role(x_user_role)

    if x_user_id is None:
        raise CodedHTTPException(status_code=400, code="validation_error", detail="x-user-id header missing")
    try:
        return int(x_user_id)
    except ValueError as exc:
        raise CodedHTTPException(status_code=400, code="validation_error", detail="x-user-id must be integer") from exc
