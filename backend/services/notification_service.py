"""Notification orchestration for order events."""
from __future__ import annotations

from backend.repositories.notification_repository import NotificationRepository
from backend.schemas.employee import EmployeeOrder, MealSelection
from backend.schemas.notification import Notification


class NotificationService:
    def __init__(self, repository: NotificationRepository) -> None:
        self._repository = repository

    def list_unread(self, recipient_user_id: int) -> list[Notification]:
        return self._repository.list_unread(recipient_user_id=recipient_user_id)

    def create_order_placed(self, order: EmployeeOrder) -> Notification:
        return self._repository.create(
            recipient_user_id=order.employee_id,
            type="order_placed",
            payload={
                "order_id": order.id,
                "vendor_id": order.vendor_id,
                "status": order.status,
                "meal_date": order.meal_date.isoformat() if order.meal_date else None,
                "total_price_cents": order.total_price_cents,
            },
        )

    def create_order_placed_for_selection(self, selection: MealSelection) -> Notification:
        return self._repository.create(
            recipient_user_id=selection.employee_id,
            type="order_placed",
            payload={
                "order_id": selection.order_id,
                "vendor_id": selection.vendor_id,
                "status": "pending",
                "meal_date": selection.meal_date.isoformat() if selection.meal_date else None,
                "total_price_cents": selection.total_price_cents,
            },
        )

    def create_order_status_updated(self, order: EmployeeOrder) -> Notification:
        return self._repository.create(
            recipient_user_id=order.employee_id,
            type="order_status_updated",
            payload={
                "order_id": order.id,
                "vendor_id": order.vendor_id,
                "status": order.status,
                "meal_date": order.meal_date.isoformat() if order.meal_date else None,
            },
        )

    def create_billing_statement_ready(
        self,
        *,
        recipient_user_id: int,
        year: int,
        month: int,
        amount_cents: int,
    ) -> Notification:
        return self._repository.create(
            recipient_user_id=recipient_user_id,
            type="billing.statement_ready",
            payload={"year": year, "month": month, "amount_cents": amount_cents},
        )

    def create_payroll_deduction_posted(
        self,
        *,
        recipient_user_id: int,
        year: int,
        month: int,
        amount_cents: int,
    ) -> Notification:
        return self._repository.create(
            recipient_user_id=recipient_user_id,
            type="payroll.deduction_posted",
            payload={"year": year, "month": month, "amount_cents": amount_cents},
        )
