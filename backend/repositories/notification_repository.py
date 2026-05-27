"""In-memory notification persistence for tests and local no-DB mode."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import count
from typing import Any

from backend.schemas.notification import Notification


@dataclass
class _NotificationRecord:
    id: int
    recipient_user_id: int
    type: str
    payload: dict[str, Any]
    sent_at: datetime | None
    read_at: datetime | None
    created_at: datetime


class NotificationRepository:
    def __init__(self) -> None:
        self._notifications: dict[int, _NotificationRecord] = {}
        self._id_seq = count(1)

    def create(
        self,
        *,
        recipient_user_id: int,
        type: str,
        payload: dict[str, Any],
    ) -> Notification:
        now = datetime.now(timezone.utc)
        record = _NotificationRecord(
            id=next(self._id_seq),
            recipient_user_id=recipient_user_id,
            type=type,
            payload=dict(payload),
            sent_at=now,
            read_at=None,
            created_at=now,
        )
        self._notifications[record.id] = record
        return self._to_schema(record)

    def list_unread(self, *, recipient_user_id: int) -> list[Notification]:
        rows = [
            row
            for row in self._notifications.values()
            if row.recipient_user_id == recipient_user_id and row.read_at is None
        ]
        rows.sort(key=lambda row: (row.sent_at or row.created_at, row.id), reverse=True)
        return [self._to_schema(row) for row in rows]

    @staticmethod
    def _to_schema(record: _NotificationRecord) -> Notification:
        return Notification(
            id=record.id,
            recipient_user_id=record.recipient_user_id,
            type=record.type,
            payload=dict(record.payload),
            sent_at=record.sent_at,
            read_at=record.read_at,
            created_at=record.created_at,
        )
