"""Audit log repository singletons + selection factory."""
from __future__ import annotations

from backend.core.config import settings
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.repositories.postgres_audit_log_repository import PostgresAuditLogRepository

_IN_MEMORY = AuditLogRepository()
_POSTGRES = PostgresAuditLogRepository()


def get_audit_log_repository():
    if settings.database_url:
        return _POSTGRES
    return _IN_MEMORY
