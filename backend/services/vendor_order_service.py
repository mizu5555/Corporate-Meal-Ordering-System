"""Vendor order management: list, detail, and status transition."""
from __future__ import annotations

from datetime import date

from backend.core.errors import CodedHTTPException
from backend.core.masking import mask_name
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
        user_repo=None,
    ) -> None:
        self._repo = selection_repo
        self._vendor_repo = vendor_repo
        self._audit = audit_log_repository or AuditLogRepository()
        self._user_repo = user_repo

    def _list_orders_raw(self, vendor_id: int, facility_id: int | None = None) -> list[EmployeeOrder]:
        """Internal: vendor's orders WITH employee_id intact (for label/facility lookup)."""
        self._assert_facility_access(vendor_id, facility_id)
        return self._repo.list_orders_by_vendor(vendor_id=vendor_id, facility_id=facility_id)

    def _get_order_raw(self, vendor_id: int, order_id: int) -> EmployeeOrder:
        """Internal: single order WITH employee_id intact (for label/facility lookup)."""
        order = self._repo.get_order_for_vendor(vendor_id=vendor_id, order_id=order_id)
        if order is None:
            raise CodedHTTPException(status_code=404, code="not_found", detail="order not found")
        return order

    def list_orders(self, vendor_id: int, facility_id: int | None = None) -> list[EmployeeOrder]:
        orders = self._list_orders_raw(vendor_id, facility_id=facility_id)
        return [self._deidentify_order(order) for order in orders]

    def list_pickup_labels(
        self,
        vendor_id: int,
        *,
        facility_id: int | None = None,
        meal_date: date | None = None,
        status: OrderStatus | None = None,
    ) -> list[PickupLabel]:
        orders = self._list_orders_raw(vendor_id, facility_id=facility_id)
        if meal_date is not None:
            orders = [order for order in orders if order.meal_date == meal_date]
        if status is not None:
            orders = [order for order in orders if order.status == status]
        return [self._deidentify_label(self._order_to_label(order)) for order in orders]

    def get_order(self, vendor_id: int, order_id: int) -> EmployeeOrder:
        return self._deidentify_order(self._get_order_raw(vendor_id, order_id))

    def get_pickup_label(self, vendor_id: int, order_id: int) -> PickupLabel:
        return self._deidentify_label(self._order_to_label(self._get_order_raw(vendor_id, order_id)))

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
        return self._deidentify_order(updated)

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

    def list_ready_orders_by_badge(self, vendor_id, badge_code, *, meal_date=None):
        if self._user_repo is None:
            return []
        user = self._user_repo.get_by_badge_code(badge_code)
        if user is None:
            raise CodedHTTPException(
                status_code=404, code="badge_not_found", detail="no employee with this badge"
            )
        orders = self._repo.list_orders_by_employee_for_vendor(
            vendor_id=vendor_id, employee_id=user.id, status="ready", meal_date=meal_date
        )
        # by-badge is the one path that attaches employee identity (badge + masked name)
        return [self._label_order(o) for o in orders]

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

    def _employee_label(self, employee_id):
        """(badge_code, masked_name) for an employee via the user directory.
        Used only by the by-badge path (a later task). General paths don't call this."""
        if employee_id is None or self._user_repo is None:
            return None, None
        user = self._user_repo.get_by_id(employee_id)
        if user is None:
            return None, None
        return user.badge_code, mask_name(user.display_name)

    def _deidentify_order(self, order):
        # general vendor paths: drop uid, carry no identity
        return order.model_copy(update={"employee_id": None})

    def _label_order(self, order):
        # by-badge path only: clear uid AND attach badge + masked name
        badge, masked = self._employee_label(order.employee_id)
        return order.model_copy(
            update={"employee_id": None, "employee_badge_code": badge, "masked_name": masked}
        )

    def _deidentify_label(self, label):
        # general vendor label path: clear internal source id, add no identity
        return label.model_copy(update={"source_employee_id": None})

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
            source_employee_id=order.employee_id,
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
