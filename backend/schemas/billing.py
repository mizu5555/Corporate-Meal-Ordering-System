from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class VendorReceivable(BaseModel):
    vendor_id: int
    vendor_name: str
    owner_user_id: int | None = None
    order_count: int
    quantity: int
    amount_cents: int


class EmployeeTotal(BaseModel):
    employee_id: int
    employee_name: str | None = None
    amount_cents: int


class MonthlyStatement(BaseModel):
    year: int
    month: int
    generated_at: datetime
    vendors: list[VendorReceivable]
    employees: list[EmployeeTotal]
