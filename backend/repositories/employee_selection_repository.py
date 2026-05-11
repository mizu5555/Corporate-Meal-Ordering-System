"""In-memory employee meal selection repository."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import count

from backend.schemas.employee import MealSelection


@dataclass
class _SelectionRecord:
    id: int
    employee_id: int
    vendor_id: int
    item_id: int
    item_name: str
    quantity: int
    unit_price_cents: int
    created_at: datetime


def _to_schema(rec: _SelectionRecord) -> MealSelection:
    return MealSelection(
        id=rec.id,
        employee_id=rec.employee_id,
        vendor_id=rec.vendor_id,
        item_id=rec.item_id,
        item_name=rec.item_name,
        quantity=rec.quantity,
        unit_price_cents=rec.unit_price_cents,
        total_price_cents=rec.quantity * rec.unit_price_cents,
        created_at=rec.created_at,
    )


class EmployeeSelectionRepository:
    def __init__(self) -> None:
        self._rows: dict[int, _SelectionRecord] = {}
        self._id_seq = count(1)

    def create(
        self,
        *,
        employee_id: int,
        vendor_id: int,
        item_id: int,
        item_name: str,
        quantity: int,
        unit_price_cents: int,
    ) -> MealSelection:
        rec = _SelectionRecord(
            id=next(self._id_seq),
            employee_id=employee_id,
            vendor_id=vendor_id,
            item_id=item_id,
            item_name=item_name,
            quantity=quantity,
            unit_price_cents=unit_price_cents,
            created_at=datetime.now(timezone.utc),
        )
        self._rows[rec.id] = rec
        return _to_schema(rec)

    def list(self, *, employee_id: int) -> list[MealSelection]:
        rows = [r for r in self._rows.values() if r.employee_id == employee_id]
        rows.sort(key=lambda r: r.id)
        return [_to_schema(r) for r in rows]
