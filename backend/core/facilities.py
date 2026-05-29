"""Facility repository singletons + selection factory."""
from __future__ import annotations

from backend.core.config import settings
from backend.repositories.facility_repository import FacilityRepository
from backend.repositories.postgres_facility_repository import PostgresFacilityRepository

_IN_MEMORY = FacilityRepository()
_POSTGRES = PostgresFacilityRepository()


def get_facility_repository():
    if settings.database_url:
        return _POSTGRES
    return _IN_MEMORY
