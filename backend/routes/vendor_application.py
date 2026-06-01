"""Vendor application — lets a vendor_manager submit a new vendor profile for admin review."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from backend.core.errors import CodedHTTPException
from backend.core.facilities import get_facility_repository
from backend.core.vendor_identity import require_vendor_manager
from backend.repositories.vendor_repository import VendorRepository
from backend.schemas.vendor import VendorApplicationCreate, VendorApplicationDetail
from backend.schemas.vendor_self import Facility

router = APIRouter(prefix="/vendor/applications", tags=["vendor-application"])

_repo = VendorRepository()


def get_vendor_repository() -> VendorRepository:
    return _repo


_REQUIRED_APPLICATION_FIELDS = {
    "vendor_name": "vendor_name",
    "address": "address",
    "business_hours": "business_hours",
    "contact_phone": "contact_phone",
    "contact_email": "contact_email",
}


def _validate_application_payload(payload: VendorApplicationCreate, facility_repo) -> VendorApplicationCreate:
    missing = [
        label
        for field, label in _REQUIRED_APPLICATION_FIELDS.items()
        if not (getattr(payload, field) or "").strip()
    ]
    facility_ids = list(dict.fromkeys(payload.facility_ids))
    if not facility_ids:
        missing.append("facility_ids")
    if missing:
        raise CodedHTTPException(
            status_code=400,
            code="validation_error",
            detail=f"missing required fields: {', '.join(missing)}",
        )

    invalid_ids = [facility_id for facility_id in facility_ids if not facility_repo.facility_exists(facility_id)]
    if invalid_ids:
        raise CodedHTTPException(
            status_code=400,
            code="validation_error",
            detail=f"facility not found: {', '.join(str(fid) for fid in invalid_ids)}",
        )

    return payload.model_copy(update={"facility_ids": facility_ids})


@router.get("/facilities", response_model=list[Facility])
def list_application_facilities(
    _user_id: Annotated[int, Depends(require_vendor_manager)],
    facility_repo: Annotated[object, Depends(get_facility_repository)],
) -> list[Facility]:
    return facility_repo.list_facilities()


@router.post("", response_model=VendorApplicationDetail, status_code=status.HTTP_201_CREATED)
def submit_application(
    payload: VendorApplicationCreate,
    user_id: Annotated[int, Depends(require_vendor_manager)],
    repo: Annotated[VendorRepository, Depends(get_vendor_repository)],
    facility_repo: Annotated[object, Depends(get_facility_repository)],
) -> VendorApplicationDetail:
    existing = repo.get_my_application(user_id)
    if existing is not None:
        raise CodedHTTPException(
            status_code=409,
            code="application_already_exists",
            detail="A vendor application already exists for this account",
        )
    payload = _validate_application_payload(payload, facility_repo)
    return repo.create_application(user_id, payload)


@router.get("/me", response_model=VendorApplicationDetail | None)
def get_my_application(
    user_id: Annotated[int, Depends(require_vendor_manager)],
    repo: Annotated[VendorRepository, Depends(get_vendor_repository)],
) -> VendorApplicationDetail | None:
    return repo.get_my_application(user_id)
