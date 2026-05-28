"""Vendor order management: list, detail, and status transition."""
from __future__ import annotations

from backend.core.errors import CodedHTTPException
from backend.repositories.employee_selection_repository import EmployeeSelectionRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository
from backend.schemas.employee import EmployeeOrder

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
    ) -> None:
        self._repo = selection_repo
        self._vendor_repo = vendor_repo

    def list_orders(self, vendor_id: int, facility_id: int | None = None) -> list[EmployeeOrder]:
        self._assert_facility_access(vendor_id, facility_id)
        return self._repo.list_orders_by_vendor(vendor_id=vendor_id, facility_id=facility_id)

    def get_order(self, vendor_id: int, order_id: int) -> EmployeeOrder:
        order = self._repo.get_order_for_vendor(vendor_id=vendor_id, order_id=order_id)
        if order is None:
            raise CodedHTTPException(status_code=404, code="not_found", detail="order not found")
        return order

    def update_status(self, vendor_id: int, order_id: int, new_status: str) -> EmployeeOrder:
        order = self.get_order(vendor_id, order_id)
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
