from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from backend.core.audit import get_audit_log_repository
from backend.core.errors import CodedHTTPException
from backend.core.rbac import get_current_user_id, require_roles
from backend.db.connection import get_connection
from backend.schemas.admin import AdminUserItem, AdminUserListResponse

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


def _fetch_users(search: str | None, role: str | None) -> list[dict]:
    conditions = ["1=1"]
    params: list = []

    if search:
        conditions.append("(u.email ILIKE %s OR u.display_name ILIKE %s)")
        pattern = f"%{search}%"
        params.extend([pattern, pattern])

    if role:
        conditions.append("r.name = %s")
        params.append(role)

    where = " AND ".join(conditions)
    sql = f"""
        SELECT u.id, u.email, u.display_name, r.name AS role, u.is_active, u.created_at
        FROM users u
        JOIN roles r ON r.id = u.role_id
        WHERE {where}
        ORDER BY u.created_at DESC
    """
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


@router.get("", response_model=AdminUserListResponse)
def list_users(
    _role: Annotated[str, Depends(require_roles("admin"))],
    search: str | None = Query(default=None),
    role: str | None = Query(default=None),
) -> AdminUserListResponse:
    users = _fetch_users(search, role)
    return AdminUserListResponse(
        users=[AdminUserItem(**u) for u in users],
        total=len(users),
    )


@router.patch("/{user_id}/disable", status_code=status.HTTP_200_OK)
def disable_user(
    user_id: int,
    _role: Annotated[str, Depends(require_roles("admin"))],
    actor_id: Annotated[int | None, Depends(get_current_user_id)],
    repo: Annotated[object, Depends(get_audit_log_repository)],
) -> dict:
    if actor_id == user_id:
        raise CodedHTTPException(
            status_code=403,
            code="cannot_disable_self",
            detail="Admin cannot disable their own account",
        )
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM users WHERE id = %s", (user_id,)).fetchone()
        if not row:
            raise CodedHTTPException(status_code=404, code="user_not_found", detail="User not found")
        conn.execute("UPDATE users SET is_active = FALSE, updated_at = NOW() WHERE id = %s", (user_id,))
        conn.commit()
    repo.record(actor_user_id=actor_id, actor_role="admin",
                action="user.disable", target_type="user", target_id=user_id)
    return {"user_id": user_id, "is_active": False}


@router.patch("/{user_id}/enable", status_code=status.HTTP_200_OK)
def enable_user(
    user_id: int,
    _role: Annotated[str, Depends(require_roles("admin"))],
    actor_id: Annotated[int | None, Depends(get_current_user_id)],
    repo: Annotated[object, Depends(get_audit_log_repository)],
) -> dict:
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM users WHERE id = %s", (user_id,)).fetchone()
        if not row:
            raise CodedHTTPException(status_code=404, code="user_not_found", detail="User not found")
        conn.execute("UPDATE users SET is_active = TRUE, updated_at = NOW() WHERE id = %s", (user_id,))
        conn.commit()
    repo.record(actor_user_id=actor_id, actor_role="admin",
                action="user.enable", target_type="user", target_id=user_id)
    return {"user_id": user_id, "is_active": True}


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    _role: Annotated[str, Depends(require_roles("admin"))],
    actor_id: Annotated[int | None, Depends(get_current_user_id)],
    repo: Annotated[object, Depends(get_audit_log_repository)],
) -> None:
    if actor_id == user_id:
        raise CodedHTTPException(
            status_code=403,
            code="cannot_delete_self",
            detail="Admin cannot delete their own account",
        )
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM users WHERE id = %s", (user_id,)).fetchone()
        if not row:
            raise CodedHTTPException(status_code=404, code="user_not_found", detail="User not found")
        conn.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
    repo.record(actor_user_id=actor_id, actor_role="admin",
                action="user.delete", target_type="user", target_id=user_id)
