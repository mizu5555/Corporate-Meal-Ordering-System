"""Vendor identity dependency.

JWT-first: reads vendor_id from Bearer token payload.
Header fallback: x-user-role + x-vendor-id (keeps existing tests working).
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Request

from backend.core.config import settings
from backend.core.errors import CodedHTTPException
from backend.core.security import decode_access_token
from backend.repositories.postgres_vendor_profile_repository import PostgresVendorProfileRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository

_REPO_SINGLETON = VendorProfileRepository()
_POSTGRES_REPO_SINGLETON = PostgresVendorProfileRepository()


def get_vendor_profile_repository() -> VendorProfileRepository:
    if settings.database_url:
        return _POSTGRES_REPO_SINGLETON
    return _REPO_SINGLETON


def require_approved_vendor(
    request: Request,
    repo: Annotated[VendorProfileRepository, Depends(get_vendor_profile_repository)],
    x_user_role: Annotated[str | None, Header()] = None,
    x_vendor_id: Annotated[str | None, Header()] = None,
) -> int:
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        payload = decode_access_token(auth[7:])
        if payload:
            if payload.get("role") != "vendor_manager":
                raise CodedHTTPException(status_code=403, code="forbidden", detail="vendor role required")
            vendor_id = payload.get("vendor_id")
            if vendor_id is None:
                raise CodedHTTPException(status_code=403, code="vendor_not_approved", detail="no approved vendor linked to this account")
            record = repo.get(vendor_id)
            if record is None:
                raise CodedHTTPException(status_code=404, code="not_found", detail="vendor not found")
            if record.status != "approved":
                raise CodedHTTPException(status_code=403, code="vendor_not_approved", detail="vendor not approved")
            return vendor_id

    # Header fallback (tests / mock login)
    if x_user_role != "vendor_manager":
        raise CodedHTTPException(status_code=403, code="forbidden", detail="vendor role required")
    if x_vendor_id is None:
        raise CodedHTTPException(status_code=400, code="validation_error", detail="x-vendor-id header missing")
    try:
        vendor_id = int(x_vendor_id)
    except ValueError as exc:
        raise CodedHTTPException(status_code=400, code="validation_error", detail="x-vendor-id must be integer") from exc
    record = repo.get(vendor_id)
    if record is None:
        raise CodedHTTPException(status_code=404, code="not_found", detail="vendor not found")
    if record.status != "approved":
        raise CodedHTTPException(status_code=403, code="vendor_not_approved", detail="vendor not approved")
    return vendor_id
