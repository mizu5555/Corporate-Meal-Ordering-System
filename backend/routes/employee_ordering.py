"""Employee-facing vendor browsing, menu browsing, and meal selection APIs."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from backend.core.config import settings
from backend.core.employee_identity import require_employee, require_employee_role
from backend.core.vendor_identity import get_vendor_profile_repository
from backend.repositories.employee_selection_repository import EmployeeSelectionRepository
from backend.repositories.menu_item_repository import MenuItemRepository
from backend.repositories.postgres_employee_selection_repository import PostgresEmployeeSelectionRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository
from backend.routes.vendor_menu import get_menu_item_repository
from backend.schemas.employee import EmployeeMenuItem, EmployeeVendor, MealSelection, MealSelectionCreate
from backend.services.employee_ordering_service import EmployeeOrderingService

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
    _employee_role: Annotated[None, Depends(require_employee_role)],
    service: Annotated[EmployeeOrderingService, Depends(get_employee_ordering_service)],
) -> list[EmployeeVendor]:
    return service.list_vendors()


@router.get("/vendors/{vendor_id}", response_model=EmployeeVendor)
def get_vendor(
    vendor_id: int,
    _employee_role: Annotated[None, Depends(require_employee_role)],
    service: Annotated[EmployeeOrderingService, Depends(get_employee_ordering_service)],
) -> EmployeeVendor:
    return service.get_vendor(vendor_id)


@router.get("/vendors/{vendor_id}/menu", response_model=list[EmployeeMenuItem])
def list_menu(
    vendor_id: int,
    _employee_role: Annotated[None, Depends(require_employee_role)],
    service: Annotated[EmployeeOrderingService, Depends(get_employee_ordering_service)],
    category_id: Annotated[int | None, Query()] = None,
    available: Annotated[bool | None, Query()] = True,
) -> list[EmployeeMenuItem]:
    return service.list_menu(vendor_id, category_id=category_id, available=available)


@router.post("/vendors/{vendor_id}/selections", response_model=MealSelection, status_code=status.HTTP_201_CREATED)
def select_meal(
    vendor_id: int,
    payload: MealSelectionCreate,
    employee_id: Annotated[int, Depends(require_employee)],
    service: Annotated[EmployeeOrderingService, Depends(get_employee_ordering_service)],
) -> MealSelection:
    return service.select_meal(employee_id, vendor_id, payload)


@router.get("/me/selections", response_model=list[MealSelection])
def list_my_selections(
    employee_id: Annotated[int, Depends(require_employee)],
    service: Annotated[EmployeeOrderingService, Depends(get_employee_ordering_service)],
) -> list[MealSelection]:
    return service.list_my_selections(employee_id)
