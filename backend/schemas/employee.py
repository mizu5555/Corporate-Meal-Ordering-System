"""Employee-facing vendor, menu, and meal selection schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from backend.schemas.vendor_self import Facility


class EmployeeVendor(BaseModel):
    id: int
    name: str
    address: str | None = None
    business_hours: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    served_facilities: list[Facility] = Field(default_factory=list)


class EmployeeMenuItem(BaseModel):
    id: int
    vendor_id: int
    category_id: int | None
    name: str
    description: str | None
    price_cents: int
    available: bool
    daily_quota: int | None
    photo_path: str | None


class MealSelectionCreate(BaseModel):
    item_id: int
    quantity: int = Field(ge=1)


class MealSelection(BaseModel):
    id: int
    employee_id: int
    vendor_id: int
    item_id: int
    item_name: str
    quantity: int
    unit_price_cents: int
    total_price_cents: int
    created_at: datetime
