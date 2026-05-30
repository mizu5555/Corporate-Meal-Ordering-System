"""In-memory audit log persistence for tests and local no-DB mode."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import count

from backend.schemas.audit import AuditLogEntry


@dataclass
class _AuditRecord:
    id: int
    actor_user_id: int | None
    actor_role: str | None
    action: str
    target_type: str
    target_id: int | None
    metadata: dict
    created_at: datetime


class AuditLogRepository:
    def __init__(self) -> None:
        self._rows: list[_AuditRecord] = []
        self._id_seq = count(1)

    def record(self, *, actor_user_id: int | None, actor_role: str | None,
               action: str, target_type: str, target_id: int | None = None,
               metadata: dict | None = None) -> None:
        self._rows.append(_AuditRecord(
            id=next(self._id_seq), actor_user_id=actor_user_id, actor_role=actor_role,
            action=action, target_type=target_type, target_id=target_id,
            metadata=dict(metadata or {}), created_at=datetime.now(timezone.utc),
        ))

    def list(self, *, limit: int = 50, offset: int = 0, action: str | None = None,
             actor_user_id: int | None = None, target_type: str | None = None,
             target_id: int | None = None) -> list[AuditLogEntry]:
        rows = [
            r for r in self._rows
            if (action is None or r.action == action)
            and (actor_user_id is None or r.actor_user_id == actor_user_id)
            and (target_type is None or r.target_type == target_type)
            and (target_id is None or r.target_id == target_id)
        ]
        rows.sort(key=lambda r: (r.created_at, r.id), reverse=True)
        rows = rows[offset:offset + limit]
        return [self._to_schema(r) for r in rows]

    @staticmethod
    def _to_schema(r: _AuditRecord) -> AuditLogEntry:
        return AuditLogEntry(
            id=r.id, actor_user_id=r.actor_user_id, actor_role=r.actor_role,
            action=r.action, target_type=r.target_type, target_id=r.target_id,
            metadata=dict(r.metadata), created_at=r.created_at,
        )
