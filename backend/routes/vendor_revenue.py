from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.core.reporting import get_reporting_repository
from backend.core.vendor_identity import get_vendor_profile_repository, require_approved_vendor
from backend.repositories.menu_item_repository import MenuItemRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository
from backend.routes.vendor_menu import get_menu_item_repository
from backend.schemas.vendor_revenue import VendorRevenueDashboard
from backend.services.vendor_revenue_service import VendorRevenueService

router = APIRouter(prefix="/vendor/me/revenue", tags=["vendor-self"])


def get_vendor_revenue_service(
    item_repo: Annotated[MenuItemRepository, Depends(get_menu_item_repository)],
    reporting_repo: Annotated[object, Depends(get_reporting_repository)],
    vendor_repo: Annotated[VendorProfileRepository, Depends(get_vendor_profile_repository)],
) -> VendorRevenueService:
    return VendorRevenueService(item_repo, reporting_repo, vendor_repo)


@router.get("")
def get_vendor_revenue(
    vendor_id: Annotated[int, Depends(require_approved_vendor)],
    service: Annotated[VendorRevenueService, Depends(get_vendor_revenue_service)],
    today: Annotated[date | None, Query()] = None,
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
    facility_id: Annotated[int | None, Query()] = None,
) -> VendorRevenueDashboard:
    report_today = today or date.today()
    report_end = end or report_today
    report_start = start or (report_end - timedelta(days=29))
    return service.dashboard(
        vendor_id,
        today=report_today,
        start=report_start,
        end=report_end,
        facility_id=facility_id,
    )
