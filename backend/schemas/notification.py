"""Notification response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Notification(BaseModel):
    id: int
    recipient_user_id: int
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    sent_at: datetime | None = None
    read_at: datetime | None = None
    created_at: datetime
