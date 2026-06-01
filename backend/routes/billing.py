from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from backend.core.employee_identity import require_employee
from backend.core.rbac import get_current_user_id, get_current_user_role, require_roles
from backend.core.reporting import get_reporting_repository
from backend.core.vendor_identity import require_approved_vendor
from backend.schemas.billing import MonthlyBillingSummary, MonthlyStatement, VendorReceivable
from backend.services.billing_service import BillingService

router = APIRouter(tags=["billing"])


def _service(repo) -> BillingService:
    return BillingService(reporting_repository=repo)


def _period(year: int | None, month: int | None) -> tuple[int, int]:
    today = date.today()
    return year or today.year, month or today.month


@router.get("/employee/me/billing", response_model=MonthlyBillingSummary)
def get_my_employee_billing(
    employee_id: Annotated[int, Depends(require_employee)],
    repo: Annotated[object, Depends(get_reporting_repository)],
    year: Annotated[int | None, Query(ge=2000, le=9999)] = None,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
) -> MonthlyBillingSummary:
    y, m = _period(year, month)
    return _service(repo).employee_billing(employee_id, y, m)


@router.get("/vendor/me/billing", response_model=MonthlyBillingSummary)
def get_my_vendor_billing(
    vendor_id: Annotated[int, Depends(require_approved_vendor)],
    repo: Annotated[object, Depends(get_reporting_repository)],
    year: Annotated[int | None, Query(ge=2000, le=9999)] = None,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
) -> MonthlyBillingSummary:
    y, m = _period(year, month)
    return _service(repo).vendor_billing(vendor_id, y, m)


@router.get("/admin/billing/vendors", response_model=list[VendorReceivable])
def vendor_receivables(
    _role: Annotated[str, Depends(require_roles("admin", "committee_reviewer"))],
    repo: Annotated[object, Depends(get_reporting_repository)],
    year: Annotated[int, Query()],
    month: Annotated[int, Query()],
) -> list[VendorReceivable]:
    return _service(repo).vendor_receivables(year, month)


@router.get("/admin/billing/vendors.csv")
def vendor_receivables_csv(
    _role: Annotated[str, Depends(require_roles("admin", "committee_reviewer"))],
    repo: Annotated[object, Depends(get_reporting_repository)],
    year: Annotated[int, Query()],
    month: Annotated[int, Query()],
) -> Response:
    csv_text = _service(repo).vendor_receivables_csv(year, month)
    filename = f"vendor-receivables-{year:04d}-{month:02d}.csv"
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/admin/billing/payroll")
def payroll(
    _role: Annotated[str, Depends(require_roles("admin", "committee_reviewer"))],
    repo: Annotated[object, Depends(get_reporting_repository)],
    year: Annotated[int, Query()],
    month: Annotated[int, Query()],
) -> list[dict]:
    return _service(repo).employee_payroll(year, month)


@router.get("/admin/billing/payroll.csv")
def payroll_csv(
    _role: Annotated[str, Depends(require_roles("admin", "committee_reviewer"))],
    repo: Annotated[object, Depends(get_reporting_repository)],
    year: Annotated[int, Query()],
    month: Annotated[int, Query()],
) -> Response:
    csv_text = _service(repo).employee_payroll_csv(year, month)
    filename = f"payroll-deductions-{year:04d}-{month:02d}.csv"
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/admin/billing/statements", response_model=MonthlyStatement)
def generate_statement(
    _role: Annotated[str, Depends(require_roles("admin", "committee_reviewer"))],
    repo: Annotated[object, Depends(get_reporting_repository)],
    year: Annotated[int, Query()],
    month: Annotated[int, Query()],
    actor_id: Annotated[int | None, Depends(get_current_user_id)] = None,
    actor_role: Annotated[str, Depends(get_current_user_role)] = "anonymous",
) -> MonthlyStatement:
    return _service(repo).generate_statement(year, month, actor_user_id=actor_id, actor_role=actor_role)
