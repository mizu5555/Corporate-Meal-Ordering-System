"""Employee-facing vendor browsing, menu browsing, and meal selection APIs."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, status

from backend.core.config import settings
from backend.core.employee_identity import require_employee
from backend.core.vendor_identity import get_vendor_profile_repository
from backend.repositories.employee_selection_repository import EmployeeSelectionRepository
from backend.repositories.menu_item_repository import MenuItemRepository
from backend.repositories.postgres_employee_selection_repository import PostgresEmployeeSelectionRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository
from backend.routes.vendor_menu import get_menu_item_repository
from backend.routes.notifications import get_notification_service
from backend.schemas.employee import (
    EmployeeMenuItem,
    EmployeeOrder,
    EmployeeOrderCreate,
    EmployeeOrderUpdate,
    EmployeeVendor,
    MealSelection,
    MealSelectionCreate,
    PickupLabel,
    RandomMealDraw,
    RandomMealDrawRequest,
)
from backend.schemas.vendor_self import Facility
from backend.services.employee_ordering_service import EmployeeOrderingService
from backend.services.notification_service import NotificationService

router = APIRouter(prefix="/employee", tags=["employee"])

_selection_repo = EmployeeSelectionRepository()
_postgres_selection_repo = PostgresEmployeeSelectionRepository()


def get_employee_selection_repository() -> EmployeeSelectionRepository | PostgresEmployeeSelectionRepository:
    if settings.database_url:
        return _postgres_selection_repo
    return _selection_repo


def get_employee_ordering_service(
    vendor_repo: Annotated[VendorProfileRepository, Depends(get_vendor_profile_repository)],
    item_repo: Annotated[MenuItemRepository, Depends(get_menu_item_repository)],
    selection_repo: Annotated[EmployeeSelectionRepository, Depends(get_employee_selection_repository)],
) -> EmployeeOrderingService:
    return EmployeeOrderingService(vendor_repo, item_repo, selection_repo)


@router.get("/vendors", response_model=list[EmployeeVendor])
def list_vendors(
    employee_id: Annotated[int, Depends(require_employee)],
    service: Annotated[EmployeeOrderingService, Depends(get_employee_ordering_service)],
    facility_id: Annotated[int | None, Query()] = None,
) -> list[EmployeeVendor]:
    return service.list_vendors(employee_id=employee_id, facility_id=facility_id)


@router.get("/vendors/{vendor_id}", response_model=EmployeeVendor)
def get_vendor(
    vendor_id: int,
    employee_id: Annotated[int, Depends(require_employee)],
    service: Annotated[EmployeeOrderingService, Depends(get_employee_ordering_service)],
    facility_id: Annotated[int | None, Query()] = None,
) -> EmployeeVendor:
    return service.get_vendor(vendor_id, employee_id=employee_id, facility_id=facility_id)


@router.get("/vendors/{vendor_id}/menu", response_model=list[EmployeeMenuItem])
def list_menu(
    vendor_id: int,
    employee_id: Annotated[int, Depends(require_employee)],
    service: Annotated[EmployeeOrderingService, Depends(get_employee_ordering_service)],
    category_id: Annotated[int | None, Query()] = None,
    available: Annotated[bool | None, Query()] = True,
    facility_id: Annotated[int | None, Query()] = None,
) -> list[EmployeeMenuItem]:
    return service.list_menu(
        vendor_id,
        category_id=category_id,
        available=available,
        employee_id=employee_id,
        facility_id=facility_id,
    )


@router.get("/me/facilities", response_model=list[Facility])
def list_my_facilities(
    employee_id: Annotated[int, Depends(require_employee)],
    service: Annotated[EmployeeOrderingService, Depends(get_employee_ordering_service)],
) -> list[Facility]:
    return service.list_employee_facilities(employee_id)


@router.post("/random-meals/draw", response_model=RandomMealDraw)
def draw_random_meal(
    payload: RandomMealDrawRequest,
    employee_id: Annotated[int, Depends(require_employee)],
    service: Annotated[EmployeeOrderingService, Depends(get_employee_ordering_service)],
) -> RandomMealDraw:
    return service.draw_random_meal(payload, employee_id=employee_id)


@router.post("/vendors/{vendor_id}/selections", response_model=MealSelection, status_code=status.HTTP_201_CREATED)
def select_meal(
    vendor_id: int,
    payload: MealSelectionCreate,
    background_tasks: BackgroundTasks,
    employee_id: Annotated[int, Depends(require_employee)],
    service: Annotated[EmployeeOrderingService, Depends(get_employee_ordering_service)],
    notification_service: Annotated[NotificationService, Depends(get_notification_service)],
) -> MealSelection:
    selection = service.select_meal(employee_id, vendor_id, payload)
    background_tasks.add_task(notification_service.create_order_placed_for_selection, selection)
    return selection


@router.post("/vendors/{vendor_id}/orders", response_model=EmployeeOrder, status_code=status.HTTP_201_CREATED)
def create_order(
    vendor_id: int,
    payload: EmployeeOrderCreate,
    background_tasks: BackgroundTasks,
    employee_id: Annotated[int, Depends(require_employee)],
    service: Annotated[EmployeeOrderingService, Depends(get_employee_ordering_service)],
    notification_service: Annotated[NotificationService, Depends(get_notification_service)],
) -> EmployeeOrder:
    order = service.create_order(employee_id, vendor_id, payload)
    background_tasks.add_task(notification_service.create_order_placed, order)
    return order


@router.get("/me/selections", response_model=list[MealSelection])
def list_my_selections(
    employee_id: Annotated[int, Depends(require_employee)],
    service: Annotated[EmployeeOrderingService, Depends(get_employee_ordering_service)],
) -> list[MealSelection]:
    return service.list_my_selections(employee_id)


@router.get("/me/orders", response_model=list[EmployeeOrder])
def list_my_orders(
    employee_id: Annotated[int, Depends(require_employee)],
    service: Annotated[EmployeeOrderingService, Depends(get_employee_ordering_service)],
) -> list[EmployeeOrder]:
    return service.list_my_orders(employee_id)


@router.get("/me/orders/{order_id}", response_model=EmployeeOrder)
def get_my_order(
    order_id: int,
    employee_id: Annotated[int, Depends(require_employee)],
    service: Annotated[EmployeeOrderingService, Depends(get_employee_ordering_service)],
) -> EmployeeOrder:
    return service.get_my_order(employee_id, order_id)


@router.get("/me/orders/{order_id}/pickup-label", response_model=PickupLabel)
def get_my_pickup_label(
    order_id: int,
    employee_id: Annotated[int, Depends(require_employee)],
    service: Annotated[EmployeeOrderingService, Depends(get_employee_ordering_service)],
) -> PickupLabel:
    return service.get_my_pickup_label(employee_id, order_id)


@router.put("/me/orders/{order_id}", response_model=EmployeeOrder)
def update_my_order(
    order_id: int,
    payload: EmployeeOrderUpdate,
    employee_id: Annotated[int, Depends(require_employee)],
    service: Annotated[EmployeeOrderingService, Depends(get_employee_ordering_service)],
) -> EmployeeOrder:
    return service.update_my_order(employee_id, order_id, payload)


@router.post("/me/orders/{order_id}/cancel", response_model=EmployeeOrder)
def cancel_my_order(
    order_id: int,
    employee_id: Annotated[int, Depends(require_employee)],
    service: Annotated[EmployeeOrderingService, Depends(get_employee_ordering_service)],
) -> EmployeeOrder:
    return service.cancel_my_order(employee_id, order_id)


@router.delete("/me/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_order(
    order_id: int,
    employee_id: Annotated[int, Depends(require_employee)],
    service: Annotated[EmployeeOrderingService, Depends(get_employee_ordering_service)],
) -> Response:
    service.cancel_my_order(employee_id, order_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
