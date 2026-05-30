from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from backend.core.config import settings
from backend.core.employee_identity import require_employee
from backend.core.rbac import require_roles
from backend.core.vendor_identity import get_vendor_profile_repository, require_approved_vendor
from backend.repositories.employee_selection_repository import EmployeeSelectionRepository
from backend.repositories.postgres_reporting_repository import PostgresReportingRepository
from backend.repositories.reporting_repository import ReportingRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository
from backend.routes.employee_ordering import get_employee_selection_repository
from backend.schemas.billing import EmployeeTotal, MonthlyBillingSummary, VendorReceivable
from backend.services.billing_service import BillingService

router = APIRouter(tags=["billing"])

_postgres_reporting_repo = PostgresReportingRepository()


def _period(year: int | None, month: int | None) -> tuple[int, int]:
    today = date.today()
    return year or today.year, month or today.month


def get_reporting_repository(
    selection_repo: Annotated[EmployeeSelectionRepository, Depends(get_employee_selection_repository)],
    vendor_repo: Annotated[VendorProfileRepository, Depends(get_vendor_profile_repository)],
) -> ReportingRepository | PostgresReportingRepository:
    if settings.database_url:
        return _postgres_reporting_repo
    return ReportingRepository(selection_repo, vendor_repo)


def get_billing_service(
    reporting_repo: Annotated[ReportingRepository | PostgresReportingRepository, Depends(get_reporting_repository)],
) -> BillingService:
    return BillingService(reporting_repo)


@router.get("/employee/me/billing", response_model=MonthlyBillingSummary)
def get_my_employee_billing(
    employee_id: Annotated[int, Depends(require_employee)],
    service: Annotated[BillingService, Depends(get_billing_service)],
    year: Annotated[int | None, Query(ge=2000, le=9999)] = None,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
) -> MonthlyBillingSummary:
    y, m = _period(year, month)
    return service.employee_billing(employee_id, y, m)


@router.get("/vendor/me/billing", response_model=MonthlyBillingSummary)
def get_my_vendor_billing(
    vendor_id: Annotated[int, Depends(require_approved_vendor)],
    service: Annotated[BillingService, Depends(get_billing_service)],
    year: Annotated[int | None, Query(ge=2000, le=9999)] = None,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
) -> MonthlyBillingSummary:
    y, m = _period(year, month)
    return service.vendor_billing(vendor_id, y, m)


@router.get("/admin/billing/vendors", response_model=list[VendorReceivable])
def list_vendor_receivables(
    _role: Annotated[str, Depends(require_roles("admin", "committee_reviewer"))],
    service: Annotated[BillingService, Depends(get_billing_service)],
    year: Annotated[int | None, Query(ge=2000, le=9999)] = None,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
) -> list[VendorReceivable]:
    y, m = _period(year, month)
    return service.vendor_receivables(y, m)


@router.get("/admin/billing/vendors.csv")
def export_vendor_receivables_csv(
    _role: Annotated[str, Depends(require_roles("admin", "committee_reviewer"))],
    service: Annotated[BillingService, Depends(get_billing_service)],
    year: Annotated[int | None, Query(ge=2000, le=9999)] = None,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
) -> Response:
    y, m = _period(year, month)
    filename = f"vendor-receivables-{y:04d}-{m:02d}.csv"
    return Response(
        service.vendor_receivables_csv(y, m),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/admin/billing/payroll", response_model=list[EmployeeTotal])
def list_employee_payroll(
    _role: Annotated[str, Depends(require_roles("admin", "committee_reviewer"))],
    service: Annotated[BillingService, Depends(get_billing_service)],
    year: Annotated[int | None, Query(ge=2000, le=9999)] = None,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
) -> list[EmployeeTotal]:
    y, m = _period(year, month)
    return service.employee_payroll(y, m)


@router.get("/admin/billing/payroll.csv")
def export_employee_payroll_csv(
    _role: Annotated[str, Depends(require_roles("admin", "committee_reviewer"))],
    service: Annotated[BillingService, Depends(get_billing_service)],
    year: Annotated[int | None, Query(ge=2000, le=9999)] = None,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
) -> Response:
    y, m = _period(year, month)
    filename = f"payroll-deductions-{y:04d}-{m:02d}.csv"
    return Response(
        service.employee_payroll_csv(y, m),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
