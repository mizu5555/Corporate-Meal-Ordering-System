"""Employee-facing vendor browsing, menu browsing, and ordering workflow."""
from __future__ import annotations

import random
from datetime import date, timedelta

from backend.core.errors import CodedHTTPException
from backend.core.reporting import get_reporting_repository
from backend.core.order_failure_codes import ITEM_UNAVAILABLE, QUOTA_EXHAUSTED
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.repositories.employee_selection_repository import EmployeeSelectionRepository, OrderItemSnapshot
from backend.repositories.menu_item_repository import MenuItemRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository, VendorRecord
from backend.schemas.employee import (
    EmployeeMenuItem,
    EmployeeOrder,
    EmployeeOrderCreate,
    EmployeeOrderItemCreate,
    EmployeeOrderUpdate,
    EmployeeVendor,
    MealSelection,
    MealSelectionCreate,
    PickupLabel,
    PickupLabelItem,
    RandomMealDraw,
    RandomMealDrawRequest,
    RecommendedItem,
)
from backend.schemas.vendor_self import Facility, MenuItem as VendorMenuItem

MEAL_DATE_WINDOW_DAYS = 7


class EmployeeOrderingService:
    def __init__(
        self,
        vendor_repository: VendorProfileRepository,
        menu_item_repository: MenuItemRepository,
        selection_repository: EmployeeSelectionRepository,
        audit_log_repository: AuditLogRepository | None = None,
        reporting_repository=None,
    ) -> None:
        self.vendor_repository = vendor_repository
        self.menu_item_repository = menu_item_repository
        self.selection_repository = selection_repository
        self.audit_log_repository = audit_log_repository or AuditLogRepository()
        self.reporting_repository = reporting_repository or get_reporting_repository()

    def list_vendors(
        self,
        employee_id: int | None = None,
        facility_id: int | None = None,
    ) -> list[EmployeeVendor]:
        vendors = [self._vendor_to_schema(vendor) for vendor in self.vendor_repository.list(status="approved")]
        if employee_id is None:
            return vendors
        return self._filter_vendors_by_facility(vendors, employee_id, facility_id=facility_id)

    def get_vendor(
        self,
        vendor_id: int,
        employee_id: int | None = None,
        facility_id: int | None = None,
    ) -> EmployeeVendor:
        vendor = self._vendor_to_schema(self._get_approved_vendor(vendor_id))
        if employee_id is not None:
            self._assert_facility_access(vendor, employee_id, facility_id=facility_id)
        return vendor

    def list_menu(
        self,
        vendor_id: int,
        *,
        category_id: int | None = None,
        available: bool | None = True,
        employee_id: int | None = None,
        facility_id: int | None = None,
    ) -> list[EmployeeMenuItem]:
        vendor = self._vendor_to_schema(self._get_approved_vendor(vendor_id))
        if employee_id is not None:
            self._assert_facility_access(vendor, employee_id, facility_id=facility_id)
        return [
            self._menu_item_to_schema(item)
            for item in self.menu_item_repository.list(
                vendor_id=vendor_id,
                category_id=category_id,
                available=available,
            )
        ]

    def select_meal(
        self,
        employee_id: int,
        vendor_id: int,
        payload: MealSelectionCreate,
    ) -> MealSelection:
        order = self.create_order(
            employee_id,
            vendor_id,
            EmployeeOrderCreate(
                meal_date=payload.meal_date,
                facility_id=payload.facility_id,
                items=[
                    EmployeeOrderItemCreate(
                        item_id=payload.item_id,
                        quantity=payload.quantity,
                    )
                ],
            ),
            actor_user_id=employee_id,
        )
        item = order.items[0]
        return MealSelection(
            id=item.id,
            order_id=order.id,
            employee_id=order.employee_id,
            vendor_id=order.vendor_id,
            facility_id=order.facility_id,
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
        self,
        employee_id: int,
        vendor_id: int,
        payload: EmployeeOrderCreate,
        *,
        actor_user_id: int | None = None,
    ) -> EmployeeOrder:
        vendor = self._vendor_to_schema(self._get_approved_vendor(vendor_id))
        facility_id = self._resolve_order_facility(employee_id, vendor, payload.facility_id)
        meal_date = payload.meal_date or date.today()
        self._ensure_meal_date_in_window(meal_date)
        snapshots = self._build_order_items(vendor_id, payload, meal_date=meal_date)
        order = self.selection_repository.create_order(
            employee_id=employee_id,
            vendor_id=vendor_id,
            items=snapshots,
            meal_date=meal_date,
            facility_id=facility_id,
        )
        self.audit_log_repository.record(
            actor_user_id=actor_user_id,
            actor_role="employee",
            action="order.create",
            target_type="order",
            target_id=order.id,
            metadata={"vendor_id": order.vendor_id, "total_cents": order.total_price_cents},
        )
        return order

    def draw_random_meal(
        self,
        payload: RandomMealDrawRequest,
        employee_id: int | None = None,
    ) -> RandomMealDraw:
        self._ensure_meal_date_in_window(payload.meal_date)
        all_approved = self.vendor_repository.list(status="approved")

        if employee_id is not None:
            visible = self._filter_vendors_by_facility(
                [self._vendor_to_schema(v) for v in all_approved],
                employee_id,
                facility_id=payload.facility_id,
            )
            visible_ids = {v.id for v in visible}
            approved_vendors = {v.id: v for v in all_approved if v.id in visible_ids}
        else:
            approved_vendors = {vendor.id: vendor for vendor in all_approved}

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

    def recommend(
        self,
        *,
        employee_id: int | None = None,
        facility_id: int | None = None,
        meal_date: date | None = None,
        limit: int = 8,
    ) -> list[RecommendedItem]:
        target_date = meal_date or date.today()

        # Build visible approved vendor schemas (reuse same pattern as draw_random_meal)
        all_approved = self.vendor_repository.list(status="approved")
        if employee_id is not None:
            visible = self._filter_vendors_by_facility(
                [self._vendor_to_schema(v) for v in all_approved],
                employee_id,
                facility_id=facility_id,
            )
        else:
            visible = [self._vendor_to_schema(v) for v in all_approved]

        if not visible:
            return []

        visible_ids = [v.id for v in visible]
        vendor_by_id = {v.id: v for v in visible}

        used = self.selection_repository.item_quantities_for_date(
            meal_date=target_date,
            vendor_ids=visible_ids,
        )

        # Build item_by_id: {item_id: (vendor_id, raw_item)}
        item_by_id: dict[int, tuple[int, object]] = {}
        for vid in visible_ids:
            for it in self.menu_item_repository.list(vendor_id=vid, available=True):
                item_by_id[it.id] = (vid, it)

        # Sales window: past 30 days up to today
        end = date.today()
        start = end - timedelta(days=29)
        ranked = self.reporting_repository.top_items(
            start, end, limit=limit * 3, vendor_ids=visible_ids
        )

        results: list[RecommendedItem] = []
        for sale in ranked:
            if len(results) >= limit:
                break
            entry = item_by_id.get(sale.item_id)
            if entry is None:
                continue
            vid, it = entry
            remaining = self._remaining_quantity(it, used.get(it.id, 0))
            if remaining is not None and remaining <= 0:
                continue
            results.append(
                RecommendedItem(
                    vendor=vendor_by_id[vid],
                    item=self._menu_item_to_schema(it),
                    quantity_sold=sale.quantity_sold,
                    remaining_quantity=remaining,
                    from_sales=True,
                )
            )

        # Fallback: if no sales data, return available items
        if not results:
            for it_id, (vid, it) in item_by_id.items():
                if len(results) >= limit:
                    break
                remaining = self._remaining_quantity(it, used.get(it.id, 0))
                if remaining is not None and remaining <= 0:
                    continue
                results.append(
                    RecommendedItem(
                        vendor=vendor_by_id[vid],
                        item=self._menu_item_to_schema(it),
                        quantity_sold=0,
                        remaining_quantity=remaining,
                        from_sales=False,
                    )
                )

        return results

    def list_my_orders(self, employee_id: int) -> list[EmployeeOrder]:
        return self.selection_repository.list_orders(employee_id=employee_id)

    def get_my_order(self, employee_id: int, order_id: int) -> EmployeeOrder:
        order = self.selection_repository.get_order(employee_id=employee_id, order_id=order_id)
        if order is None:
            raise CodedHTTPException(status_code=404, code="not_found", detail="order not found")
        return order

    def get_my_pickup_label(self, employee_id: int, order_id: int) -> PickupLabel:
        return self._order_to_pickup_label(self.get_my_order(employee_id, order_id))

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

    def update_my_order(
        self,
        employee_id: int,
        order_id: int,
        payload: EmployeeOrderUpdate,
    ) -> EmployeeOrder:
        order = self.get_my_order(employee_id, order_id)
        if order.status != "pending":
            raise CodedHTTPException(
                status_code=409,
                code="order_not_modifiable",
                detail="only pending orders can be modified",
            )

        vendor = self._vendor_to_schema(self._get_approved_vendor(order.vendor_id))
        meal_date = payload.meal_date or order.meal_date or date.today()
        self._ensure_meal_date_in_window(meal_date)
        facility_id = (
            self._resolve_order_facility(employee_id, vendor, payload.facility_id)
            if payload.facility_id is not None
            else order.facility_id
        )
        snapshots = self._build_order_items(
            order.vendor_id,
            EmployeeOrderCreate(meal_date=meal_date, facility_id=facility_id, items=payload.items),
            meal_date=meal_date,
            exclude_order_id=order.id,
        )
        updated = self.selection_repository.update_order(
            employee_id=employee_id,
            order_id=order_id,
            items=snapshots,
            meal_date=meal_date,
            facility_id=facility_id,
        )
        if updated is None:
            raise CodedHTTPException(status_code=404, code="not_found", detail="order not found")
        return updated

    def list_employee_facilities(self, employee_id: int) -> list[Facility]:
        return self.vendor_repository.list_employee_facilities(employee_id)

    def _filter_vendors_by_facility(
        self,
        vendors: list[EmployeeVendor],
        employee_id: int,
        *,
        facility_id: int | None = None,
    ) -> list[EmployeeVendor]:
        employee_facilities = self.vendor_repository.list_employee_facilities(employee_id)
        if not employee_facilities:
            if facility_id is not None:
                raise CodedHTTPException(
                    status_code=403,
                    code="forbidden",
                    detail="employee is not assigned to the selected facility",
                )
            return vendors

        employee_fids = self._employee_facility_ids(employee_facilities, facility_id)
        result = []
        for vendor in vendors:
            if not vendor.served_facilities:
                result.append(vendor)
            elif any(f.id in employee_fids for f in vendor.served_facilities):
                result.append(vendor)
        return result

    def _assert_facility_access(
        self,
        vendor: EmployeeVendor,
        employee_id: int,
        *,
        facility_id: int | None = None,
    ) -> None:
        employee_facilities = self.vendor_repository.list_employee_facilities(employee_id)
        if not employee_facilities:
            if facility_id is not None:
                raise CodedHTTPException(
                    status_code=403,
                    code="forbidden",
                    detail="employee is not assigned to the selected facility",
                )
            return
        if not vendor.served_facilities:
            return
        employee_fids = self._employee_facility_ids(employee_facilities, facility_id)
        if not any(f.id in employee_fids for f in vendor.served_facilities):
            raise CodedHTTPException(status_code=404, code="not_found", detail="vendor not found")

    def _resolve_order_facility(
        self,
        employee_id: int,
        vendor: EmployeeVendor,
        requested_facility_id: int | None,
    ) -> int | None:
        employee_facilities = self.vendor_repository.list_employee_facilities(employee_id)
        if not employee_facilities:
            if requested_facility_id is not None:
                raise CodedHTTPException(
                    status_code=403,
                    code="forbidden",
                    detail="employee is not assigned to the selected facility",
                )
            return None

        employee_fids = self._employee_facility_ids(employee_facilities, requested_facility_id)
        vendor_fids = {f.id for f in vendor.served_facilities}
        candidates = employee_fids if not vendor_fids else employee_fids & vendor_fids
        if not candidates:
            raise CodedHTTPException(status_code=404, code="not_found", detail="vendor not found")
        if requested_facility_id is not None:
            return requested_facility_id
        if len(candidates) == 1:
            return next(iter(candidates))
        raise CodedHTTPException(
            status_code=400,
            code="facility_required",
            detail="facility_id is required when multiple facilities are available",
        )

    @staticmethod
    def _employee_facility_ids(
        employee_facilities: list[Facility],
        facility_id: int | None,
    ) -> set[int]:
        employee_fids = {f.id for f in employee_facilities}
        if facility_id is None:
            return employee_fids
        if facility_id not in employee_fids:
            raise CodedHTTPException(
                status_code=403,
                code="forbidden",
                detail="employee is not assigned to the selected facility",
            )
        return {facility_id}

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

    def _order_to_pickup_label(self, order: EmployeeOrder) -> PickupLabel:
        vendor = self.vendor_repository.get(order.vendor_id)
        employee_facilities = self.vendor_repository.list_employee_facilities(order.employee_id)
        facilities = employee_facilities or self.vendor_repository.list_facilities(order.vendor_id)
        items = [
            PickupLabelItem(item_name=item.item_name, quantity=item.quantity)
            for item in order.items
        ]
        return PickupLabel(
            order_id=order.id,
            pickup_code=order.pickup_code,
            employee_id=order.employee_id,
            vendor_id=order.vendor_id,
            vendor_name=vendor.name if vendor else f"Vendor #{order.vendor_id}",
            meal_date=order.meal_date,
            status=order.status,
            facility_names=[facility.name for facility in facilities],
            items=items,
            total_quantity=sum(item.quantity for item in order.items),
            total_price_cents=order.total_price_cents,
            pickup_confirmed_at=order.pickup_confirmed_at,
            pickup_confirmed_by_user_id=order.pickup_confirmed_by_user_id,
        )

    def _build_order_items(
        self,
        vendor_id: int,
        payload: EmployeeOrderCreate,
        *,
        meal_date: date,
        exclude_order_id: int | None = None,
    ) -> list[OrderItemSnapshot]:
        requested_by_item: dict[int, int] = {}
        for requested in payload.items:
            requested_by_item[requested.item_id] = (
                requested_by_item.get(requested.item_id, 0) + requested.quantity
            )

        used_by_item = self.selection_repository.item_quantities_for_date(
            meal_date=meal_date,
            vendor_ids=[vendor_id],
            exclude_order_id=exclude_order_id,
        )
        snapshots: list[OrderItemSnapshot] = []
        for requested in payload.items:
            item = self.menu_item_repository.get(vendor_id=vendor_id, item_id=requested.item_id)
            if item is None:
                raise CodedHTTPException(status_code=404, code="not_found", detail="menu item not found")
            used_quantity = used_by_item.get(item.id, 0)
            if not item.available:
                if item.daily_quota is not None and used_quantity >= item.daily_quota:
                    raise CodedHTTPException(
                        status_code=409,
                        code=QUOTA_EXHAUSTED,
                        detail="quantity exceeds remaining daily quota",
                    )
                raise CodedHTTPException(status_code=409, code=ITEM_UNAVAILABLE, detail="menu item unavailable")
            if item.daily_quota is not None and used_quantity + requested_by_item[item.id] > item.daily_quota:
                raise CodedHTTPException(
                    status_code=409,
                    code=QUOTA_EXHAUSTED,
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

    @staticmethod
    def _ensure_meal_date_in_window(meal_date: date) -> None:
        today = date.today()
        max_date = today + timedelta(days=MEAL_DATE_WINDOW_DAYS - 1)
        if meal_date < today or meal_date > max_date:
            raise CodedHTTPException(
                status_code=400,
                code="validation_error",
                detail="meal date must be within today and the next 6 days",
            )
