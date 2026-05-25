"""Vendor application — lets a vendor_manager submit a new vendor profile for admin review."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from backend.core.vendor_identity import require_vendor_manager
from backend.repositories.vendor_repository import VendorRepository
from backend.schemas.vendor import VendorApplicationCreate, VendorApplicationDetail

router = APIRouter(prefix="/vendor/applications", tags=["vendor-application"])

_repo = VendorRepository()


def get_vendor_repository() -> VendorRepository:
    return _repo


@router.post("", response_model=VendorApplicationDetail, status_code=status.HTTP_201_CREATED)
def submit_application(
    payload: VendorApplicationCreate,
    user_id: Annotated[int, Depends(require_vendor_manager)],
    repo: Annotated[VendorRepository, Depends(get_vendor_repository)],
) -> VendorApplicationDetail:
    existing = repo.get_my_application(user_id)
    if existing is not None:
        from backend.core.errors import CodedHTTPException
        raise CodedHTTPException(
            status_code=409,
            code="application_already_exists",
            detail="A vendor application already exists for this account",
        )
    return repo.create_application(user_id, payload)


@router.get("/me", response_model=VendorApplicationDetail | None)
def get_my_application(
    user_id: Annotated[int, Depends(require_vendor_manager)],
    repo: Annotated[VendorRepository, Depends(get_vendor_repository)],
) -> VendorApplicationDetail | None:
    return repo.get_my_application(user_id)
