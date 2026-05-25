"""Employee-facing read and meal selection workflow."""
from __future__ import annotations

import random
from datetime import date

from backend.core.errors import CodedHTTPException
from backend.repositories.employee_selection_repository import EmployeeSelectionRepository, OrderItemSnapshot
from backend.repositories.menu_item_repository import MenuItemRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository, VendorRecord
from backend.schemas.employee import (
    EmployeeMenuItem,
    EmployeeOrder,
    EmployeeOrderCreate,
    EmployeeOrderItemCreate,
    EmployeeVendor,
    MealSelection,
    MealSelectionCreate,
    RandomMealDraw,
    RandomMealDrawRequest,
)
from backend.schemas.vendor_self import MenuItem as VendorMenuItem


class EmployeeOrderingService:
    def __init__(
        self,
        vendor_repository: VendorProfileRepository,
        menu_item_repository: MenuItemRepository,
        selection_repository: EmployeeSelectionRepository,
    ) -> None:
        self.vendor_repository = vendor_repository
        self.menu_item_repository = menu_item_repository
        self.selection_repository = selection_repository

    def list_vendors(self) -> list[EmployeeVendor]:
        return [self._vendor_to_schema(vendor) for vendor in self.vendor_repository.list(status="approved")]

    def get_vendor(self, vendor_id: int) -> EmployeeVendor:
        return self._vendor_to_schema(self._get_approved_vendor(vendor_id))

    def list_menu(
        self, vendor_id: int, *, category_id: int | None = None, available: bool | None = True
    ) -> list[EmployeeMenuItem]:
        self._get_approved_vendor(vendor_id)
        return [
            self._menu_item_to_schema(item)
            for item in self.menu_item_repository.list(
                vendor_id=vendor_id, category_id=category_id, available=available
            )
        ]

    def select_meal(
        self, employee_id: int, vendor_id: int, payload: MealSelectionCreate
    ) -> MealSelection:
        order = self.create_order(
            employee_id,
            vendor_id,
            EmployeeOrderCreate(
                meal_date=payload.meal_date,
                items=[
                    EmployeeOrderItemCreate(
                        item_id=payload.item_id,
                        quantity=payload.quantity,
                    )
                ]
            ),
        )
        item = order.items[0]
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
            total_price_cents=item.total_price_cents,
            created_at=order.created_at,
        )

    def list_my_selections(self, employee_id: int) -> list[MealSelection]:
        return self.selection_repository.list(employee_id=employee_id)

    def create_order(
        self, employee_id: int, vendor_id: int, payload: EmployeeOrderCreate
    ) -> EmployeeOrder:
        self._get_approved_vendor(vendor_id)
        meal_date = payload.meal_date or date.today()
        snapshots = self._build_order_items(vendor_id, payload, meal_date=meal_date)
        return self.selection_repository.create_order(
            employee_id=employee_id,
            vendor_id=vendor_id,
            items=snapshots,
            meal_date=meal_date,
        )

    def draw_random_meal(self, payload: RandomMealDrawRequest) -> RandomMealDraw:
        approved_vendors = {vendor.id: vendor for vendor in self.vendor_repository.list(status="approved")}
        if payload.vendor_ids is None:
            vendor_ids = list(approved_vendors)
        else:
            vendor_ids = list(dict.fromkeys(payload.vendor_ids))

        if not vendor_ids:
            raise CodedHTTPException(
                status_code=400,
                code="validation_error",
                detail="at least one vendor must be selected",
            )

        missing_vendor_ids = [vendor_id for vendor_id in vendor_ids if vendor_id not in approved_vendors]
        if missing_vendor_ids:
            raise CodedHTTPException(status_code=404, code="not_found", detail="vendor not found")

        used_by_item = self.selection_repository.item_quantities_for_date(
            meal_date=payload.meal_date,
            vendor_ids=vendor_ids,
        )
        candidates: list[tuple[VendorRecord, VendorMenuItem, int | None]] = []
        for vendor_id in vendor_ids:
            vendor = approved_vendors[vendor_id]
            for item in self.menu_item_repository.list(vendor_id=vendor_id, available=True):
                remaining = self._remaining_quantity(item, used_by_item.get(item.id, 0))
                if remaining is None or remaining > 0:
                    candidates.append((vendor, item, remaining))

        if not candidates:
            raise CodedHTTPException(
                status_code=409,
                code="no_random_meal_available",
                detail="no available meals remain for the selected date and vendors",
            )

        vendor, item, remaining = random.choice(candidates)
        return RandomMealDraw(
            meal_date=payload.meal_date,
            vendor=self._vendor_to_schema(vendor),
            item=self._menu_item_to_schema(item),
            remaining_quantity=remaining,
        )

    def list_my_orders(self, employee_id: int) -> list[EmployeeOrder]:
        return self.selection_repository.list_orders(employee_id=employee_id)

    def get_my_order(self, employee_id: int, order_id: int) -> EmployeeOrder:
        order = self.selection_repository.get_order(employee_id=employee_id, order_id=order_id)
        if order is None:
            raise CodedHTTPException(status_code=404, code="not_found", detail="order not found")
        return order

    def cancel_my_order(self, employee_id: int, order_id: int) -> EmployeeOrder:
        order = self.get_my_order(employee_id, order_id)
        if order.status != "pending":
            raise CodedHTTPException(
                status_code=409,
                code="order_not_cancellable",
                detail="only pending orders can be cancelled",
            )
        cancelled = self.selection_repository.cancel_order(employee_id=employee_id, order_id=order_id)
        if cancelled is None:
            raise CodedHTTPException(status_code=404, code="not_found", detail="order not found")
        return cancelled

    def _get_approved_vendor(self, vendor_id: int) -> VendorRecord:
        vendor = self.vendor_repository.get(vendor_id)
        if vendor is None or vendor.status != "approved":
            raise CodedHTTPException(status_code=404, code="not_found", detail="vendor not found")
        return vendor

    def _vendor_to_schema(self, vendor: VendorRecord) -> EmployeeVendor:
        return EmployeeVendor(
            id=vendor.id,
            name=vendor.name,
            address=vendor.address,
            business_hours=vendor.business_hours,
            contact_phone=vendor.contact_phone,
            contact_email=vendor.contact_email,
            served_facilities=self.vendor_repository.list_facilities(vendor.id),
        )

    @staticmethod
    def _menu_item_to_schema(item: VendorMenuItem) -> EmployeeMenuItem:
        return EmployeeMenuItem(
            id=item.id,
            vendor_id=item.vendor_id,
            category_id=item.category_id,
            name=item.name,
            description=item.description,
            price_cents=item.price_cents,
            available=item.available,
            daily_quota=item.daily_quota,
            photo_path=item.photo_path,
        )

    def _build_order_items(
        self, vendor_id: int, payload: EmployeeOrderCreate, *, meal_date: date
    ) -> list[OrderItemSnapshot]:
        requested_by_item: dict[int, int] = {}
        for requested in payload.items:
            requested_by_item[requested.item_id] = (
                requested_by_item.get(requested.item_id, 0) + requested.quantity
            )

        used_by_item = self.selection_repository.item_quantities_for_date(
            meal_date=meal_date,
            vendor_ids=[vendor_id],
        )
        snapshots: list[OrderItemSnapshot] = []
        for requested in payload.items:
            item = self.menu_item_repository.get(vendor_id=vendor_id, item_id=requested.item_id)
            if item is None:
                raise CodedHTTPException(status_code=404, code="not_found", detail="menu item not found")
            if not item.available:
                raise CodedHTTPException(status_code=409, code="item_unavailable", detail="menu item unavailable")
            used_quantity = used_by_item.get(item.id, 0)
            if item.daily_quota is not None and used_quantity + requested_by_item[item.id] > item.daily_quota:
                raise CodedHTTPException(
                    status_code=409,
                    code="quantity_exceeds_daily_quota",
                    detail="quantity exceeds remaining daily quota",
                )

            snapshots.append(
                OrderItemSnapshot(
                    item_id=item.id,
                    item_name=item.name,
                    quantity=requested.quantity,
                    unit_price_cents=item.price_cents,
                )
            )
        return snapshots

    @staticmethod
    def _remaining_quantity(item: VendorMenuItem, used_quantity: int) -> int | None:
        if item.daily_quota is None:
            return None
        return max(item.daily_quota - used_quantity, 0)
