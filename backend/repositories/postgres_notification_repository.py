"""PostgreSQL notification persistence."""
from __future__ import annotations

from typing import Any

from psycopg.types.json import Jsonb

from backend.db.connection import get_connection
from backend.schemas.notification import Notification


def _notification_to_schema(row) -> Notification:
    return Notification(**dict(row))


class PostgresNotificationRepository:
    def create(
        self,
        *,
        recipient_user_id: int,
        type: str,
        payload: dict[str, Any],
    ) -> Notification:
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO notifications (recipient_user_id, type, payload, sent_at)
                VALUES (%s, %s, %s, NOW())
                RETURNING id, recipient_user_id, type, payload, sent_at, read_at, created_at
                """,
                (recipient_user_id, type, Jsonb(payload)),
            ).fetchone()
        return _notification_to_schema(row)

    def list_unread(self, *, recipient_user_id: int) -> list[Notification]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, recipient_user_id, type, payload, sent_at, read_at, created_at
                FROM notifications
                WHERE recipient_user_id = %s AND read_at IS NULL
                ORDER BY sent_at DESC NULLS LAST, id DESC
                """,
                (recipient_user_id,),
            ).fetchall()
        return [_notification_to_schema(row) for row in rows]
