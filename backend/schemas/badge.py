"""DTOs for badge quick-pickup. Vendor-facing shapes never carry the internal uid."""
from __future__ import annotations

from pydantic import BaseModel


class EmployeeBadge(BaseModel):
    badge_code: str
    display_name: str
