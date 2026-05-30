from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AuditLogEntry(BaseModel):
    id: int
    actor_user_id: int | None = None
    actor_role: str | None = None
    action: str
    target_type: str
    target_id: int | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
