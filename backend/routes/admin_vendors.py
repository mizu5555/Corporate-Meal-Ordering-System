from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from backend.core.audit import get_audit_log_repository
from backend.core.rbac import get_current_user_id, require_roles
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.repositories.vendor_repository import VendorRepository
from backend.schemas.vendor import (
    VendorApplicationDetail,
    VendorApplicationSummary,
    VendorReviewRequest,
    VendorReviewResponse,
)
from backend.services.vendor_review_service import VendorReviewService

router = APIRouter(prefix="/admin/vendors", tags=["admin-vendors"])

_repo = VendorRepository()


def get_vendor_repository() -> VendorRepository:
    return _repo


def get_vendor_review_service(
    repo: Annotated[VendorRepository, Depends(get_vendor_repository)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> VendorReviewService:
    return VendorReviewService(
        vendor_repository=repo,
        audit_log_repository=audit_repo,
    )


@router.get("/applications", response_model=list[VendorApplicationSummary])
def list_applications(
    _role: Annotated[str, Depends(require_roles("admin"))],
    repo: Annotated[VendorRepository, Depends(get_vendor_repository)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> list[VendorApplicationSummary]:
    return repo.list_applications(status=status_filter)


@router.get("/applications/{application_id}", response_model=VendorApplicationDetail)
def get_application(
    application_id: int,
    _role: Annotated[str, Depends(require_roles("admin"))],
    repo: Annotated[VendorRepository, Depends(get_vendor_repository)],
) -> VendorApplicationDetail:
    from backend.core.errors import CodedHTTPException
    app = repo.get_application(application_id)
    if app is None:
        raise CodedHTTPException(status_code=404, code="not_found", detail="application not found")
    return app


@router.post(
    "/applications/{application_id}/review",
    response_model=VendorReviewResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def review_vendor_application(
    application_id: int,
    payload: VendorReviewRequest,
    reviewer_id: Annotated[int | None, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_roles("admin"))],
    repo: Annotated[VendorRepository, Depends(get_vendor_repository)],
    service: Annotated[VendorReviewService, Depends(get_vendor_review_service)],
) -> VendorReviewResponse:
    from backend.core.errors import CodedHTTPException
    app = repo.get_application(application_id)
    if app is None:
        raise CodedHTTPException(status_code=404, code="not_found", detail="application not found")
    return service.review_application(
        application_id,
        payload,
        actor_user_id=reviewer_id,
        actor_role="admin",
    )
