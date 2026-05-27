"""Current-user notification APIs."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.core.config import settings
from backend.core.employee_identity import require_employee
from backend.repositories.notification_repository import NotificationRepository
from backend.repositories.postgres_notification_repository import PostgresNotificationRepository
from backend.schemas.notification import Notification
from backend.services.notification_service import NotificationService

router = APIRouter(prefix="/me", tags=["notifications"])

_notification_repo = NotificationRepository()
_postgres_notification_repo = PostgresNotificationRepository()


def get_notification_repository() -> NotificationRepository | PostgresNotificationRepository:
    if settings.database_url:
        return _postgres_notification_repo
    return _notification_repo


def get_notification_service(
    repository: Annotated[
        NotificationRepository | PostgresNotificationRepository,
        Depends(get_notification_repository),
    ],
) -> NotificationService:
    return NotificationService(repository)


@router.get("/notifications", response_model=list[Notification])
def list_my_notifications(
    employee_id: Annotated[int, Depends(require_employee)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> list[Notification]:
    return service.list_unread(employee_id)
