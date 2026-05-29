from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.core.rbac import require_roles
from backend.core.reporting import get_reporting_repository
from backend.schemas.admin_stats import DashboardStats
from backend.services.admin_stats_service import AdminStatsService

router = APIRouter(prefix="/admin/stats", tags=["admin-stats"])

DEFAULT_WINDOW_DAYS = 30


@router.get("", response_model=DashboardStats)
def get_stats(
    _role: Annotated[str, Depends(require_roles("admin", "committee_reviewer"))],
    repo: Annotated[object, Depends(get_reporting_repository)],
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
) -> DashboardStats:
    resolved_end = end or date.today()
    resolved_start = start or (resolved_end - timedelta(days=DEFAULT_WINDOW_DAYS - 1))
    service = AdminStatsService(reporting_repository=repo)
    return service.dashboard(resolved_start, resolved_end)
