from datetime import datetime

from pydantic import BaseModel


class AdminUserItem(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    is_active: bool
    created_at: datetime


class AdminUserListResponse(BaseModel):
    users: list[AdminUserItem]
    total: int
