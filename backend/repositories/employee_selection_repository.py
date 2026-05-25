"""In-memory employee orders with legacy meal selection compatibility."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from itertools import count

from backend.schemas.employee import EmployeeOrder, EmployeeOrderItem, MealSelection, OrderStatus


@dataclass
class OrderItemSnapshot:
    item_id: int
    item_name: str
    quantity: int
    unit_price_cents: int


@dataclass
class _OrderRecord:
    id: int
    employee_id: int
    vendor_id: int
    meal_date: date | None
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    cancelled_at: datetime | None


@dataclass
class _OrderItemRecord:
    id: int
    order_id: int
    item_id: int
    item_name: str
    quantity: int
    unit_price_cents: int


def _item_to_schema(rec: _OrderItemRecord) -> EmployeeOrderItem:
    return EmployeeOrderItem(
        id=rec.id,
        order_id=rec.order_id,
        item_id=rec.item_id,
        item_name=rec.item_name,
        quantity=rec.quantity,
        unit_price_cents=rec.unit_price_cents,
        total_price_cents=rec.quantity * rec.unit_price_cents,
    )


def _selection_to_schema(order: _OrderRecord, item: _OrderItemRecord) -> MealSelection:
    return MealSelection(
        id=item.id,
        order_id=order.id,
        employee_id=order.employee_id,
        vendor_id=order.vendor_id,
        meal_date=order.meal_date,
        item_id=item.item_id,
        item_name=item.item_name,
        quantity=item.quantity,
        unit_price_cents=item.unit_price_cents,
        total_price_cents=item.quantity * item.unit_price_cents,
        created_at=order.created_at,
    )


class EmployeeSelectionRepository:
    def __init__(self) -> None:
        self._orders: dict[int, _OrderRecord] = {}
        self._items: dict[int, _OrderItemRecord] = {}
        self._order_id_seq = count(1)
        self._item_id_seq = count(1)

    def create_order(
        self,
        *,
        employee_id: int,
        vendor_id: int,
        items: list[OrderItemSnapshot],
        meal_date: date | None = None,
    ) -> EmployeeOrder:
        now = datetime.now(timezone.utc)
        order = _OrderRecord(
            id=next(self._order_id_seq),
            employee_id=employee_id,
            vendor_id=vendor_id,
            meal_date=meal_date,
            status="pending",
            created_at=now,
            updated_at=now,
            cancelled_at=None,
        )
        self._orders[order.id] = order

        for item in items:
            rec = _OrderItemRecord(
                id=next(self._item_id_seq),
                order_id=order.id,
                item_id=item.item_id,
                item_name=item.item_name,
                quantity=item.quantity,
                unit_price_cents=item.unit_price_cents,
            )
            self._items[rec.id] = rec

        return self._order_to_schema(order)

    def list_orders(self, *, employee_id: int) -> list[EmployeeOrder]:
        rows = [r for r in self._orders.values() if r.employee_id == employee_id]
        rows.sort(key=lambda r: r.id)
        return [self._order_to_schema(r) for r in rows]

    def get_order(self, *, employee_id: int, order_id: int) -> EmployeeOrder | None:
        order = self._orders.get(order_id)
        if order is None or order.employee_id != employee_id:
            return None
        return self._order_to_schema(order)

    def cancel_order(self, *, employee_id: int, order_id: int) -> EmployeeOrder | None:
        order = self._orders.get(order_id)
        if order is None or order.employee_id != employee_id:
            return None
        if order.status != "pending":
            return self._order_to_schema(order)

        now = datetime.now(timezone.utc)
        self._orders[order.id] = _OrderRecord(
            id=order.id,
            employee_id=order.employee_id,
            vendor_id=order.vendor_id,
            meal_date=order.meal_date,
            status="cancelled",
            created_at=order.created_at,
            updated_at=now,
            cancelled_at=now,
        )
        return self._order_to_schema(self._orders[order.id])

    def create(
        self,
        *,
        employee_id: int,
        vendor_id: int,
        item_id: int,
        item_name: str,
        quantity: int,
        unit_price_cents: int,
        meal_date: date | None = None,
    ) -> MealSelection:
        order = self.create_order(
            employee_id=employee_id,
            vendor_id=vendor_id,
            meal_date=meal_date,
            items=[
                OrderItemSnapshot(
                    item_id=item_id,
                    item_name=item_name,
                    quantity=quantity,
                    unit_price_cents=unit_price_cents,
                )
            ],
        )
        return self._order_to_selection_schemas(order.id)[0]

    def list(self, *, employee_id: int) -> list[MealSelection]:
        selections: list[MealSelection] = []
        for order in sorted(self._orders.values(), key=lambda r: r.id):
            if order.employee_id != employee_id:
                continue
            selections.extend(self._order_to_selection_schemas(order.id))
        return selections

    def list_by_vendor(self, *, vendor_id: int) -> list[MealSelection]:
        selections: list[MealSelection] = []
        for order in sorted(self._orders.values(), key=lambda r: r.id):
            if order.vendor_id != vendor_id:
                continue
            selections.extend(self._order_to_selection_schemas(order.id))
        return selections

    def item_quantities_for_date(
        self, *, meal_date: date, vendor_ids: list[int] | None = None
    ) -> dict[int, int]:
        vendor_filter = set(vendor_ids) if vendor_ids is not None else None
        quantities: dict[int, int] = {}
        for order in self._orders.values():
            if order.meal_date != meal_date or order.status == "cancelled":
                continue
            if vendor_filter is not None and order.vendor_id not in vendor_filter:
                continue
            for item in self._items.values():
                if item.order_id == order.id:
                    quantities[item.item_id] = quantities.get(item.item_id, 0) + item.quantity
        return quantities

    def _order_to_schema(self, order: _OrderRecord) -> EmployeeOrder:
        items = [r for r in self._items.values() if r.order_id == order.id]
        items.sort(key=lambda r: r.id)
        schema_items = [_item_to_schema(item) for item in items]
        return EmployeeOrder(
            id=order.id,
            employee_id=order.employee_id,
            vendor_id=order.vendor_id,
            meal_date=order.meal_date,
            status=order.status,
            items=schema_items,
            total_price_cents=sum(item.total_price_cents for item in schema_items),
            created_at=order.created_at,
            updated_at=order.updated_at,
            cancelled_at=order.cancelled_at,
        )

    def _order_to_selection_schemas(self, order_id: int) -> list[MealSelection]:
        order = self._orders[order_id]
        items = [r for r in self._items.values() if r.order_id == order_id]
        items.sort(key=lambda r: r.id)
        return [_selection_to_schema(order, item) for item in items]
