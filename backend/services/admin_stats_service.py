from __future__ import annotations

from datetime import date

from backend.core.errors import CodedHTTPException
from backend.core.reporting import get_reporting_repository
from backend.schemas.admin_stats import DashboardStats

VENDOR_RANKING_LIMIT = 10


class AdminStatsService:
    def __init__(self, reporting_repository=None) -> None:
        self.reporting_repository = reporting_repository or get_reporting_repository()

    def dashboard(self, start: date, end: date) -> DashboardStats:
        if start > end:
            raise CodedHTTPException(
                status_code=400, code="validation_error",
                detail="start must be on or before end",
            )
        repo = self.reporting_repository
        return DashboardStats(
            start=start,
            end=end,
            summary=repo.order_summary(start, end),
            vendor_ranking=repo.vendor_ranking(start, end, VENDOR_RANKING_LIMIT),
            facility_distribution=repo.facility_distribution(start, end),
            daily_trend=repo.daily_trend(start, end),
        )
