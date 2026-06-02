"""In-memory facility repository used when no DATABASE_URL is set."""
from __future__ import annotations

from backend.schemas.vendor_self import Facility


class FacilityRepository:
    """In-memory implementation of the facility admin repository."""

    def __init__(self) -> None:
        self._facilities: dict[int, Facility] = {}
        self._code_index: dict[str, int] = {}  # code -> id
        self._next_id: int = 1
        self._vendor_facilities: dict[int, list[int]] = {}    # vendor_id -> [facility_id]
        self._employee_facilities: dict[int, list[int]] = {}  # employee_id -> [facility_id]

    # ------------------------------------------------------------------
    # Facilities
    # ------------------------------------------------------------------

    def list_facilities(self) -> list[Facility]:
        """Return all facilities ordered by code."""
        return sorted(self._facilities.values(), key=lambda f: f.code)

    def create_facility(self, code: str, name: str) -> Facility:
        """Create a facility; idempotent on code (returns existing row, no name overwrite)."""
        if code in self._code_index:
            return self._facilities[self._code_index[code]]
        facility = Facility(id=self._next_id, code=code, name=name)
        self._facilities[self._next_id] = facility
        self._code_index[code] = self._next_id
        self._next_id += 1
        return facility

    def facility_exists(self, facility_id: int) -> bool:
        """Return True if a facility with the given id exists."""
        return facility_id in self._facilities

    # ------------------------------------------------------------------
    # Vendor ↔ Facility assignments
    # ------------------------------------------------------------------

    def get_vendor_facility_ids(self, vendor_id: int) -> list[int]:
        """Return the list of facility IDs assigned to a vendor."""
        return list(self._vendor_facilities.get(vendor_id, []))

    def set_vendor_facilities(self, vendor_id: int, facility_ids: list[int]) -> None:
        """Replace the vendor's facility set with the given list."""
        self._vendor_facilities[vendor_id] = list(facility_ids)

    # ------------------------------------------------------------------
    # Employee ↔ Facility assignments
    # ------------------------------------------------------------------

    def get_employee_facility_ids(self, employee_id: int) -> list[int]:
        """Return the list of facility IDs assigned to an employee."""
        return list(self._employee_facilities.get(employee_id, []))

    def set_employee_facilities(self, employee_id: int, facility_ids: list[int]) -> None:
        """Replace the employee's facility set with the given list."""
        self._employee_facilities[employee_id] = list(facility_ids)
