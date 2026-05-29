"""Reporting repository singletons + selection factory."""
from __future__ import annotations

from backend.core.config import settings
from backend.repositories.postgres_reporting_repository import PostgresReportingRepository
from backend.repositories.reporting_repository import ReportingRepository

_IN_MEMORY = ReportingRepository()
_POSTGRES = PostgresReportingRepository()


def get_reporting_repository():
    if settings.database_url:
        return _POSTGRES
    return _IN_MEMORY
