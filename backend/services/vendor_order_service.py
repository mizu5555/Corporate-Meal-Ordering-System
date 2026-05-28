"""Vendor order management: list, detail, and status transition."""
from __future__ import annotations

from datetime import date

from backend.core.errors import CodedHTTPException
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.repositories.employee_selection_repository import EmployeeSelectionRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository
from backend.schemas.employee import EmployeeOrder, OrderStatus, PickupLabel, PickupLabelItem

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"preparing"},
    "preparing": {"ready"},
    "ready": {"delivered"},
}


class VendorOrderService:
    def __init__(
        self,
        selection_repo: EmployeeSelectionRepository,
        vendor_repo: VendorProfileRepository,
        audit_log_repository: AuditLogRepository | None = None,
    ) -> None:
        self._repo = selection_repo
        self._vendor_repo = vendor_repo
        self._audit = audit_log_repository or AuditLogRepository()

    def list_orders(self, vendor_id: int, facility_id: int | None = None) -> list[EmployeeOrder]:
        self._assert_facility_access(vendor_id, facility_id)
        return self._repo.list_orders_by_vendor(vendor_id=vendor_id, facility_id=facility_id)

    def list_pickup_labels(
        self,
        vendor_id: int,
        *,
        facility_id: int | None = None,
        meal_date: date | None = None,
        status: OrderStatus | None = None,
    ) -> list[PickupLabel]:
        orders = self.list_orders(vendor_id, facility_id=facility_id)
        if meal_date is not None:
            orders = [order for order in orders if order.meal_date == meal_date]
        if status is not None:
            orders = [order for order in orders if order.status == status]
        return [self._order_to_label(order) for order in orders]

    def get_order(self, vendor_id: int, order_id: int) -> EmployeeOrder:
        order = self._repo.get_order_for_vendor(vendor_id=vendor_id, order_id=order_id)
        if order is None:
            raise CodedHTTPException(status_code=404, code="not_found", detail="order not found")
        return order

    def get_pickup_label(self, vendor_id: int, order_id: int) -> PickupLabel:
        return self._order_to_label(self.get_order(vendor_id, order_id))

    def confirm_pickup(
        self,
        vendor_id: int,
        order_id: int,
        *,
        confirmer_user_id: int | None = None,
    ) -> EmployeeOrder:
        order = self.get_order(vendor_id, order_id)
        if order.status != "ready":
            raise CodedHTTPException(
                status_code=409,
                code="order_not_ready_for_pickup",
                detail="only ready orders can be confirmed for pickup",
            )
        updated = self._repo.confirm_pickup(
            vendor_id=vendor_id,
            order_id=order_id,
            confirmer_user_id=confirmer_user_id,
        )
        if updated is None:
            raise CodedHTTPException(status_code=404, code="not_found", detail="order not found")
        return updated

    def update_status(
        self,
        vendor_id: int,
        order_id: int,
        new_status: str,
        *,
        actor_user_id: int | None = None,
    ) -> EmployeeOrder:
        order = self.get_order(vendor_id, order_id)
        old_status = order.status
        allowed = ALLOWED_TRANSITIONS.get(order.status, set())
        if new_status not in allowed:
            raise CodedHTTPException(
                status_code=409,
                code="invalid_status_transition",
                detail=f"cannot transition from '{order.status}' to '{new_status}'",
            )
        updated = self._repo.update_order_status(
            vendor_id=vendor_id, order_id=order_id, new_status=new_status
        )
        if updated is None:
            raise CodedHTTPException(status_code=404, code="not_found", detail="order not found")
        self._audit.record(
            actor_user_id=actor_user_id,
            actor_role="vendor_manager",
            action="order.status_update",
            target_type="order",
            target_id=order_id,
            metadata={"from": old_status, "to": new_status},
        )
        return updated

    def _assert_facility_access(self, vendor_id: int, facility_id: int | None) -> None:
        if facility_id is None:
            return
        served_facilities = self._vendor_repo.list_facilities(vendor_id)
        if not any(f.id == facility_id for f in served_facilities):
            raise CodedHTTPException(
                status_code=403,
                code="forbidden",
                detail="vendor does not serve the selected facility",
            )

    def _order_to_label(self, order: EmployeeOrder) -> PickupLabel:
        vendor = self._vendor_repo.get(order.vendor_id)
        employee_facilities = self._vendor_repo.list_employee_facilities(order.employee_id)
        if order.facility_id is None:
            facilities = employee_facilities or self._vendor_repo.list_facilities(order.vendor_id)
        else:
            facilities = [
                facility
                for facility in (employee_facilities or self._vendor_repo.list_facilities(order.vendor_id))
                if facility.id == order.facility_id
            ]
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
