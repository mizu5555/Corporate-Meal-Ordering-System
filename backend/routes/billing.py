from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from backend.core.rbac import get_current_user_id, get_current_user_role, require_roles
from backend.core.reporting import get_reporting_repository
from backend.schemas.billing import MonthlyStatement, VendorReceivable
from backend.services.billing_service import BillingService

router = APIRouter(prefix="/admin/billing", tags=["admin-billing"])


def _service(repo) -> BillingService:
    return BillingService(reporting_repository=repo)


@router.get("/vendors", response_model=list[VendorReceivable])
def vendor_receivables(
    _role: Annotated[str, Depends(require_roles("admin", "committee_reviewer"))],
    repo: Annotated[object, Depends(get_reporting_repository)],
    year: Annotated[int, Query()],
    month: Annotated[int, Query()],
) -> list[VendorReceivable]:
    return _service(repo).vendor_receivables(year, month)


@router.get("/vendors.csv")
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


@router.get("/payroll")
def payroll(
    _role: Annotated[str, Depends(require_roles("admin", "committee_reviewer"))],
    repo: Annotated[object, Depends(get_reporting_repository)],
    year: Annotated[int, Query()],
    month: Annotated[int, Query()],
) -> list[dict]:
    return _service(repo).employee_payroll(year, month)


@router.post("/statements", response_model=MonthlyStatement)
def generate_statement(
    _role: Annotated[str, Depends(require_roles("admin", "committee_reviewer"))],
    repo: Annotated[object, Depends(get_reporting_repository)],
    year: Annotated[int, Query()],
    month: Annotated[int, Query()],
    actor_id: Annotated[int | None, Depends(get_current_user_id)] = None,
    actor_role: Annotated[str, Depends(get_current_user_role)] = "anonymous",
) -> MonthlyStatement:
    return _service(repo).generate_statement(year, month, actor_user_id=actor_id, actor_role=actor_role)
