from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MonthlyBillingSummary(BaseModel):
    year: int
    month: int = Field(ge=1, le=12)
    amount_cents: int
    order_count: int


class VendorReceivable(BaseModel):
    vendor_id: int
    vendor_name: str
    owner_user_id: int | None = None
    order_count: int
    quantity: int = 0
    amount_cents: int


class EmployeeTotal(BaseModel):
    employee_id: int
    employee_name: str | None = None
    badge_code: str | None = None
    order_count: int = 0
    amount_cents: int


class MonthlyStatement(BaseModel):
    year: int
    month: int
    generated_at: datetime
    vendors: list[VendorReceivable]
    employees: list[EmployeeTotal]
