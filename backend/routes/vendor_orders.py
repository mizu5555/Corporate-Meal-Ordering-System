"""/vendor/me/orders — 商家訂單查詢與狀態更新。"""
from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query

from backend.core.audit import get_audit_log_repository
from backend.core.errors import CodedHTTPException
from backend.core.rbac import get_current_user_id
from backend.core.user_directory import get_user_repository
from backend.core.vendor_identity import get_vendor_profile_repository, require_approved_vendor
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.repositories.employee_selection_repository import EmployeeSelectionRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository
from backend.routes.employee_ordering import get_employee_selection_repository
from backend.routes.notifications import get_notification_service
from backend.schemas.employee import EmployeeOrder, OrderStatus, PickupLabel, VendorOrderStatusUpdate
from backend.services.notification_service import NotificationService
from backend.services.vendor_order_service import VendorOrderService

router = APIRouter(prefix="/vendor/me/orders", tags=["vendor-self"])


def get_vendor_order_service(
    selection_repo: Annotated[EmployeeSelectionRepository, Depends(get_employee_selection_repository)],
    vendor_repo: Annotated[VendorProfileRepository, Depends(get_vendor_profile_repository)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
    user_repo: Annotated[object, Depends(get_user_repository)],
) -> VendorOrderService:
    return VendorOrderService(selection_repo, vendor_repo, audit_repo, user_repo=user_repo)


def optional_header_user_id(x_user_id: Annotated[str | None, Header()] = None) -> int | None:
    if x_user_id is None:
        return None
    try:
        return int(x_user_id)
    except ValueError as exc:
        raise CodedHTTPException(
            status_code=400,
            code="validation_error",
            detail="x-user-id must be integer",
        ) from exc


@router.get("", response_model=list[EmployeeOrder])
def list_vendor_orders(
    vendor_id: Annotated[int, Depends(require_approved_vendor)],
    service: Annotated[VendorOrderService, Depends(get_vendor_order_service)],
    facility_id: Annotated[int | None, Query()] = None,
) -> list[EmployeeOrder]:
    return service.list_orders(vendor_id, facility_id=facility_id)


@router.get("/labels", response_model=list[PickupLabel])
def list_vendor_pickup_labels(
    vendor_id: Annotated[int, Depends(require_approved_vendor)],
    service: Annotated[VendorOrderService, Depends(get_vendor_order_service)],
    facility_id: Annotated[int | None, Query()] = None,
    meal_date: Annotated[date | None, Query()] = None,
    status_filter: Annotated[OrderStatus | None, Query(alias="status")] = None,
) -> list[PickupLabel]:
    return service.list_pickup_labels(
        vendor_id,
        facility_id=facility_id,
        meal_date=meal_date,
        status=status_filter,
    )


@router.get("/{order_id}/label", response_model=PickupLabel)
def get_vendor_pickup_label(
    order_id: int,
    vendor_id: Annotated[int, Depends(require_approved_vendor)],
    service: Annotated[VendorOrderService, Depends(get_vendor_order_service)],
) -> PickupLabel:
    return service.get_pickup_label(vendor_id, order_id)


@router.get("/{order_id}", response_model=EmployeeOrder)
def get_vendor_order(
    order_id: int,
    vendor_id: Annotated[int, Depends(require_approved_vendor)],
    service: Annotated[VendorOrderService, Depends(get_vendor_order_service)],
) -> EmployeeOrder:
    return service.get_order(vendor_id, order_id)


@router.post("/{order_id}/pickup-confirm", response_model=EmployeeOrder)
def confirm_vendor_order_pickup(
    order_id: int,
    vendor_id: Annotated[int, Depends(require_approved_vendor)],
    confirmer_user_id: Annotated[int | None, Depends(optional_header_user_id)],
    service: Annotated[VendorOrderService, Depends(get_vendor_order_service)],
) -> EmployeeOrder:
    return service.confirm_pickup(
        vendor_id,
        order_id,
        confirmer_user_id=confirmer_user_id,
    )


@router.patch("/{order_id}/status", response_model=EmployeeOrder)
def update_vendor_order_status(
    order_id: int,
    payload: VendorOrderStatusUpdate,
    background_tasks: BackgroundTasks,
    vendor_id: Annotated[int, Depends(require_approved_vendor)],
    actor_user_id: Annotated[int | None, Depends(get_current_user_id)],
    service: Annotated[VendorOrderService, Depends(get_vendor_order_service)],
    notification_service: Annotated[NotificationService, Depends(get_notification_service)],
) -> EmployeeOrder:
    order = service.update_status(vendor_id, order_id, payload.status, actor_user_id=actor_user_id)
    background_tasks.add_task(notification_service.create_order_status_updated, order)
    return order
