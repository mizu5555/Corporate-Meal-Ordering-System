from typing import Annotated

from fastapi import APIRouter, Depends, status

from backend.core.rbac import require_roles
from backend.schemas.vendor import VendorReviewRequest, VendorReviewResponse
from backend.services.vendor_review_service import VendorReviewService

router = APIRouter(prefix="/admin/vendors", tags=["admin-vendors"])


@router.post(
    "/{application_id}/review",
    response_model=VendorReviewResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def review_vendor_application(
    application_id: int,
    payload: VendorReviewRequest,
    _role: Annotated[str, Depends(require_roles("admin"))],
) -> VendorReviewResponse:
    service = VendorReviewService()
    return service.review_application(application_id, payload)
