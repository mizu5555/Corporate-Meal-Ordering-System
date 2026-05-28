from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.core.audit import get_audit_log_repository
from backend.core.rbac import require_roles
from backend.schemas.audit import AuditLogEntry

router = APIRouter(prefix="/admin/audit-logs", tags=["admin-audit"])


@router.get("", response_model=list[AuditLogEntry])
def list_audit_logs(
    _role: Annotated[str, Depends(require_roles("admin"))],
    repo: Annotated[object, Depends(get_audit_log_repository)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    action: str | None = Query(default=None),
    actor_user_id: int | None = Query(default=None),
    target_type: str | None = Query(default=None),
    target_id: int | None = Query(default=None),
) -> list[AuditLogEntry]:
    return repo.list(limit=limit, offset=offset, action=action, actor_user_id=actor_user_id,
                     target_type=target_type, target_id=target_id)
