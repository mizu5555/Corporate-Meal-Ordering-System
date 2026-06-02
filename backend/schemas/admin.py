from datetime import datetime

from pydantic import BaseModel


class AdminUserItem(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    badge_code: str | None = None
    is_active: bool
    created_at: datetime


class AdminUserListResponse(BaseModel):
    users: list[AdminUserItem]
    total: int
