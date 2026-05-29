"""FacilityAdminService — audited facility create and vendor assignment."""
from __future__ import annotations

from backend.core.errors import CodedHTTPException
from backend.core.facilities import get_facility_repository
from backend.core.vendor_identity import get_vendor_profile_repository
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.schemas.vendor_self import Facility


class FacilityAdminService:
    def __init__(
        self,
        facility_repository=None,
        vendor_repository=None,
        audit_log_repository: AuditLogRepository | None = None,
    ) -> None:
        self.facility_repository = facility_repository or get_facility_repository()
        self.vendor_repository = vendor_repository or get_vendor_profile_repository()
        self.audit_log_repository = audit_log_repository or AuditLogRepository()

    # ------------------------------------------------------------------
    # Facilities
    # ------------------------------------------------------------------

    def list_facilities(self) -> list[Facility]:
        return self.facility_repository.list_facilities()

    def create_facility(
        self,
        code: str,
        name: str,
        *,
        actor_user_id: int | None = None,
        actor_role: str | None = None,
    ) -> Facility:
        facility = self.facility_repository.create_facility(code, name)
        self.audit_log_repository.record(
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            action="facility.create",
            target_type="facility",
            target_id=facility.id,
            metadata={"code": code, "name": name},
        )
        return facility

    # ------------------------------------------------------------------
    # Vendor ↔ Facility assignments
    # ------------------------------------------------------------------

    def get_vendor_facilities(self, vendor_id: int) -> list[Facility]:
        self._assert_vendor_exists(vendor_id)
        facility_ids = set(self.facility_repository.get_vendor_facility_ids(vendor_id))
        return [f for f in self.facility_repository.list_facilities() if f.id in facility_ids]

    def set_vendor_facilities(
        self,
        vendor_id: int,
        facility_ids: list[int],
        *,
        actor_user_id: int | None = None,
        actor_role: str | None = None,
    ) -> list[Facility]:
        self._assert_vendor_exists(vendor_id)
        for fid in facility_ids:
            if not self.facility_repository.facility_exists(fid):
                raise CodedHTTPException(
                    status_code=404,
                    code="not_found",
                    detail="facility not found",
                )
        self.facility_repository.set_vendor_facilities(vendor_id, facility_ids)
        self.audit_log_repository.record(
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            action="facility.assign",
            target_type="vendor",
            target_id=vendor_id,
            metadata={"vendor_id": vendor_id, "facility_ids": list(facility_ids)},
        )
        return self.get_vendor_facilities(vendor_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _assert_vendor_exists(self, vendor_id: int) -> None:
        record = self.vendor_repository.get(vendor_id)
        if record is None:
            raise CodedHTTPException(
                status_code=404,
                code="not_found",
                detail="vendor not found",
            )
