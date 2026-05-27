"""/vendor/me/orders — 商家訂單查詢與狀態更新。"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.core.vendor_identity import require_approved_vendor
from backend.repositories.employee_selection_repository import EmployeeSelectionRepository
from backend.routes.employee_ordering import get_employee_selection_repository
from backend.schemas.employee import EmployeeOrder, VendorOrderStatusUpdate
from backend.services.vendor_order_service import VendorOrderService

router = APIRouter(prefix="/vendor/me/orders", tags=["vendor-self"])


def get_vendor_order_service(
    selection_repo: Annotated[EmployeeSelectionRepository, Depends(get_employee_selection_repository)],
) -> VendorOrderService:
    return VendorOrderService(selection_repo)


@router.get("", response_model=list[EmployeeOrder])
def list_vendor_orders(
    vendor_id: Annotated[int, Depends(require_approved_vendor)],
    service: Annotated[VendorOrderService, Depends(get_vendor_order_service)],
) -> list[EmployeeOrder]:
    return service.list_orders(vendor_id)


@router.get("/{order_id}", response_model=EmployeeOrder)
def get_vendor_order(
    order_id: int,
    vendor_id: Annotated[int, Depends(require_approved_vendor)],
    service: Annotated[VendorOrderService, Depends(get_vendor_order_service)],
) -> EmployeeOrder:
    return service.get_order(vendor_id, order_id)


@router.patch("/{order_id}/status", response_model=EmployeeOrder)
def update_vendor_order_status(
    order_id: int,
    payload: VendorOrderStatusUpdate,
    vendor_id: Annotated[int, Depends(require_approved_vendor)],
    service: Annotated[VendorOrderService, Depends(get_vendor_order_service)],
) -> EmployeeOrder:
    return service.update_status(vendor_id, order_id, payload.status)
