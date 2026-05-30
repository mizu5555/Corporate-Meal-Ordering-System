"""Postgres-backed user directory for badge lookups."""
from __future__ import annotations

from backend.db.connection import get_connection
from backend.repositories.user_repository import UserRecord


class PostgresUserRepository:
    def get_by_id(self, user_id: int) -> UserRecord | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT u.id, u.display_name, r.name AS role, u.badge_code
                FROM users u JOIN roles r ON r.id = u.role_id
                WHERE u.id = %s
                """,
                (user_id,),
            ).fetchone()
        return _to_record(row)

    def get_by_badge_code(self, badge_code: str) -> UserRecord | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT u.id, u.display_name, r.name AS role, u.badge_code
                FROM users u JOIN roles r ON r.id = u.role_id
                WHERE u.badge_code = %s
                """,
                (badge_code,),
            ).fetchone()
        return _to_record(row)


def _to_record(row) -> UserRecord | None:
    if row is None:
        return None
    return UserRecord(
        id=row["id"],
        display_name=row["display_name"],
        role=row["role"],
        badge_code=row["badge_code"],
    )
