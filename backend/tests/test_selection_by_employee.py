"""Unit tests for EmployeeSelectionRepository.list_orders_by_employee_for_vendor."""
from datetime import date

from backend.repositories.employee_selection_repository import EmployeeSelectionRepository


def _ready_order(repo, *, vendor_id, employee_id, meal_date):
    order = repo.create_order(employee_id=employee_id, vendor_id=vendor_id, items=[], meal_date=meal_date)
    repo.update_order_status(vendor_id=vendor_id, order_id=order.id, new_status="confirmed")
    repo.update_order_status(vendor_id=vendor_id, order_id=order.id, new_status="preparing")
    repo.update_order_status(vendor_id=vendor_id, order_id=order.id, new_status="ready")
    return order.id


def test_filters_by_employee_vendor_and_status():
    repo = EmployeeSelectionRepository()
    today = date.today()
    a = _ready_order(repo, vendor_id=1, employee_id=10, meal_date=today)
    _ready_order(repo, vendor_id=1, employee_id=20, meal_date=today)           # other employee
    # a pending (not-ready) order for emp 10 at vendor 1:
    pending = repo.create_order(employee_id=10, vendor_id=1, items=[], meal_date=today)
    _ready_order(repo, vendor_id=2, employee_id=10, meal_date=today)           # other vendor

    result = repo.list_orders_by_employee_for_vendor(
        vendor_id=1, employee_id=10, status="ready", meal_date=today
    )
    ids = [o.id for o in result]
    assert ids == [a]                 # only emp10 + vendor1 + ready
    assert pending not in ids
