"""PostgreSQL audit log persistence."""
from __future__ import annotations

from psycopg.types.json import Jsonb

from backend.db.connection import get_connection
from backend.schemas.audit import AuditLogEntry

_COLUMNS = "id, actor_user_id, actor_role, action, target_type, target_id, metadata, created_at"


class PostgresAuditLogRepository:
    def record(self, *, actor_user_id: int | None, actor_role: str | None,
               action: str, target_type: str, target_id: int | None = None,
               metadata: dict | None = None) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO audit_logs
                    (actor_user_id, actor_role, action, target_type, target_id, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (actor_user_id, actor_role, action, target_type, target_id, Jsonb(metadata or {})),
            )
            conn.commit()

    def list(self, *, limit: int = 50, offset: int = 0, action: str | None = None,
             actor_user_id: int | None = None, target_type: str | None = None,
             target_id: int | None = None) -> list[AuditLogEntry]:
        conditions = ["1=1"]
        params: list = []
        if action is not None:
            conditions.append("action = %s"); params.append(action)
        if actor_user_id is not None:
            conditions.append("actor_user_id = %s"); params.append(actor_user_id)
        if target_type is not None:
            conditions.append("target_type = %s"); params.append(target_type)
        if target_id is not None:
            conditions.append("target_id = %s"); params.append(target_id)
        where = " AND ".join(conditions)
        params.extend([limit, offset])
        with get_connection() as conn:
            rows = conn.execute(
                f"SELECT {_COLUMNS} FROM audit_logs WHERE {where} "
                "ORDER BY created_at DESC, id DESC LIMIT %s OFFSET %s",
                params,
            ).fetchall()
        return [AuditLogEntry(**dict(r)) for r in rows]
