"""Admin routes for facility management and vendor-facility assignments."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from backend.core.facilities import get_facility_repository
from backend.core.errors import CodedHTTPException
from backend.core.rbac import get_current_user_id, get_current_user_role, require_roles
from backend.core.vendor_identity import get_vendor_profile_repository
from backend.db.connection import get_connection
from backend.schemas.facility_admin import EmployeeFacilitiesUpdate, FacilityCreate, VendorFacilitiesUpdate
from backend.schemas.vendor import (
    VendorDailyRecommendationLimit,
    VendorDailyRecommendationLimitUpdate,
)
from backend.schemas.vendor_self import Facility
from backend.services.facility_admin_service import FacilityAdminService

router = APIRouter(prefix="/admin", tags=["admin-facilities"])


def _service(facility_repo, vendor_repo=None) -> FacilityAdminService:
    return FacilityAdminService(
        facility_repository=facility_repo,
        vendor_repository=vendor_repo,
    )


@router.get("/facilities", response_model=list[Facility])
def list_facilities(
    _role: Annotated[str, Depends(require_roles("admin", "committee_reviewer"))],
    repo: Annotated[object, Depends(get_facility_repository)],
) -> list[Facility]:
    return _service(repo).list_facilities()


@router.post("/facilities", response_model=Facility, status_code=status.HTTP_201_CREATED)
def create_facility(
    body: FacilityCreate,
    _role: Annotated[str, Depends(require_roles("admin", "committee_reviewer"))],
    repo: Annotated[object, Depends(get_facility_repository)],
    actor_id: Annotated[int | None, Depends(get_current_user_id)] = None,
    actor_role: Annotated[str, Depends(get_current_user_role)] = "anonymous",
) -> Facility:
    return _service(repo).create_facility(
        body.code,
        body.name,
        actor_user_id=actor_id,
        actor_role=actor_role,
    )


@router.get("/vendors/{vendor_id}/facilities", response_model=list[Facility])
def get_vendor_facilities(
    vendor_id: int,
    _role: Annotated[str, Depends(require_roles("admin", "committee_reviewer"))],
    repo: Annotated[object, Depends(get_facility_repository)],
    vendor_repo: Annotated[object, Depends(get_vendor_profile_repository)],
) -> list[Facility]:
    return _service(repo, vendor_repo).get_vendor_facilities(vendor_id)


@router.put("/vendors/{vendor_id}/facilities", response_model=list[Facility])
def set_vendor_facilities(
    vendor_id: int,
    body: VendorFacilitiesUpdate,
    _role: Annotated[str, Depends(require_roles("admin", "committee_reviewer"))],
    repo: Annotated[object, Depends(get_facility_repository)],
    vendor_repo: Annotated[object, Depends(get_vendor_profile_repository)],
    actor_id: Annotated[int | None, Depends(get_current_user_id)] = None,
    actor_role: Annotated[str, Depends(get_current_user_role)] = "anonymous",
) -> list[Facility]:
    return _service(repo, vendor_repo).set_vendor_facilities(
        vendor_id,
        body.facility_ids,
        actor_user_id=actor_id,
        actor_role=actor_role,
    )


@router.get("/vendors/{vendor_id}/recommendation-limit", response_model=VendorDailyRecommendationLimit)
def get_vendor_recommendation_limit(
    vendor_id: int,
    _role: Annotated[str, Depends(require_roles("admin"))],
    vendor_repo: Annotated[object, Depends(get_vendor_profile_repository)],
) -> VendorDailyRecommendationLimit:
    vendor = vendor_repo.get(vendor_id)
    if vendor is None:
        raise CodedHTTPException(status_code=404, code="not_found", detail="vendor not found")
    return VendorDailyRecommendationLimit(
        vendor_id=vendor_id,
        daily_recommendation_limit=vendor.daily_recommendation_limit,
    )


def _assert_employee_exists(employee_id: int) -> None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE id = %s", (employee_id,)
        ).fetchone()
    if row is None:
        raise CodedHTTPException(status_code=404, code="not_found", detail="employee not found")


@router.get("/employees/{employee_id}/facilities", response_model=list[Facility])
def get_employee_facilities(
    employee_id: int,
    _role: Annotated[str, Depends(require_roles("admin"))],
    repo: Annotated[object, Depends(get_facility_repository)],
) -> list[Facility]:
    _assert_employee_exists(employee_id)
    return _service(repo).get_employee_facilities(employee_id)


@router.put("/employees/{employee_id}/facilities", response_model=list[Facility])
def set_employee_facilities(
    employee_id: int,
    body: EmployeeFacilitiesUpdate,
    _role: Annotated[str, Depends(require_roles("admin"))],
    repo: Annotated[object, Depends(get_facility_repository)],
    actor_id: Annotated[int | None, Depends(get_current_user_id)] = None,
    actor_role: Annotated[str, Depends(get_current_user_role)] = "anonymous",
) -> list[Facility]:
    _assert_employee_exists(employee_id)
    return _service(repo).set_employee_facilities(
        employee_id,
        body.facility_ids,
        actor_user_id=actor_id,
        actor_role=actor_role,
    )


@router.put("/vendors/{vendor_id}/recommendation-limit", response_model=VendorDailyRecommendationLimit)
def set_vendor_recommendation_limit(
    vendor_id: int,
    body: VendorDailyRecommendationLimitUpdate,
    _role: Annotated[str, Depends(require_roles("admin"))],
    vendor_repo: Annotated[object, Depends(get_vendor_profile_repository)],
) -> VendorDailyRecommendationLimit:
    vendor = vendor_repo.get(vendor_id)
    if vendor is None:
        raise CodedHTTPException(status_code=404, code="not_found", detail="vendor not found")
    updated = vendor_repo.update(
        vendor_id,
        {"daily_recommendation_limit": body.daily_recommendation_limit},
    )
    assert updated is not None
    return VendorDailyRecommendationLimit(
        vendor_id=vendor_id,
        daily_recommendation_limit=updated.daily_recommendation_limit,
    )
