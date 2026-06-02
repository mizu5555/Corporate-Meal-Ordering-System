"""PostgreSQL-backed facility admin repository."""
from __future__ import annotations

from backend.db.connection import get_connection
from backend.schemas.vendor_self import Facility


class PostgresFacilityRepository:
    """Postgres implementation of the facility admin repository."""

    # ------------------------------------------------------------------
    # Facilities
    # ------------------------------------------------------------------

    def list_facilities(self) -> list[Facility]:
        """Return all facilities ordered by code."""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, code, name FROM facilities ORDER BY code"
            ).fetchall()
        return [Facility(**dict(row)) for row in rows]

    def create_facility(self, code: str, name: str) -> Facility:
        """Create a facility; idempotent on code — returns existing row, no name overwrite."""
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO facilities (code, name)
                VALUES (%s, %s)
                ON CONFLICT (code) DO UPDATE SET name = facilities.name
                RETURNING id, code, name
                """,
                (code, name),
            ).fetchone()
        return Facility(**dict(row))

    def facility_exists(self, facility_id: int) -> bool:
        """Return True if a facility with the given id exists."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM facilities WHERE id = %s",
                (facility_id,),
            ).fetchone()
        return row is not None

    # ------------------------------------------------------------------
    # Vendor ↔ Facility assignments
    # ------------------------------------------------------------------

    def get_vendor_facility_ids(self, vendor_id: int) -> list[int]:
        """Return the list of facility IDs assigned to a vendor."""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT facility_id FROM vendor_facilities WHERE vendor_id = %s",
                (vendor_id,),
            ).fetchall()
        return [row["facility_id"] for row in rows]

    def set_vendor_facilities(self, vendor_id: int, facility_ids: list[int]) -> None:
        """Replace the vendor's facility set with the given list (within one transaction)."""
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM vendor_facilities WHERE vendor_id = %s",
                (vendor_id,),
            )
            for fid in facility_ids:
                conn.execute(
                    """
                    INSERT INTO vendor_facilities (vendor_id, facility_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (vendor_id, fid),
                )

    # ------------------------------------------------------------------
    # Employee ↔ Facility assignments
    # ------------------------------------------------------------------

    def get_employee_facility_ids(self, employee_id: int) -> list[int]:
        """Return the list of facility IDs assigned to an employee."""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT facility_id FROM employee_facilities WHERE employee_id = %s",
                (employee_id,),
            ).fetchall()
        return [row["facility_id"] for row in rows]

    def set_employee_facilities(self, employee_id: int, facility_ids: list[int]) -> None:
        """Replace the employee's facility set with the given list (within one transaction)."""
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM employee_facilities WHERE employee_id = %s",
                (employee_id,),
            )
            for fid in facility_ids:
                conn.execute(
                    """
                    INSERT INTO employee_facilities (employee_id, facility_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (employee_id, fid),
                )
