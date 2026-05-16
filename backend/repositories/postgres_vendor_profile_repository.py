from __future__ import annotations

from typing import Any

from backend.db.connection import get_connection
from backend.repositories.vendor_profile_repository import VendorRecord
from backend.schemas.vendor_self import Facility


class PostgresVendorProfileRepository:
    def seed(self, record: VendorRecord) -> None:
        """Insert or update a vendor record.

        This mirrors the in-memory repository helper and is useful for local
        setup scripts or integration tests.
        """
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO vendors (
                    id, name, status, address, business_hours,
                    contact_phone, contact_email
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    status = EXCLUDED.status,
                    address = EXCLUDED.address,
                    business_hours = EXCLUDED.business_hours,
                    contact_phone = EXCLUDED.contact_phone,
                    contact_email = EXCLUDED.contact_email,
                    updated_at = NOW()
                """,
                (
                    record.id,
                    record.name,
                    record.status,
                    record.address,
                    record.business_hours,
                    record.contact_phone,
                    record.contact_email,
                ),
            )

    def assign_facility(self, vendor_id: int, *, facility_id: int, code: str, name: str) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO facilities (id, code, name)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    code = EXCLUDED.code,
                    name = EXCLUDED.name
                """,
                (facility_id, code, name),
            )
            conn.execute(
                """
                INSERT INTO vendor_facilities (vendor_id, facility_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                (vendor_id, facility_id),
            )

    def get(self, vendor_id: int) -> VendorRecord | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    id, name, status, address, business_hours,
                    contact_phone, contact_email
                FROM vendors
                WHERE id = %s
                """,
                (vendor_id,),
            ).fetchone()

        if row is None:
            return None
        return VendorRecord(**dict(row))

    def update(self, vendor_id: int, fields: dict[str, Any]) -> VendorRecord | None:
        allowed_columns = {
            "name": "name",
            "address": "address",
            "business_hours": "business_hours",
            "contact_phone": "contact_phone",
            "contact_email": "contact_email",
        }
        updates = [
            (allowed_columns[key], value)
            for key, value in fields.items()
            if key in allowed_columns
        ]
        if not updates:
            return self.get(vendor_id)

        assignments = [f"{column} = %s" for column, _ in updates]
        values = [value for _, value in updates]
        values.append(vendor_id)

        with get_connection() as conn:
            row = conn.execute(
                f"""
                UPDATE vendors
                SET {", ".join(assignments)}, updated_at = NOW()
                WHERE id = %s
                RETURNING
                    id, name, status, address, business_hours,
                    contact_phone, contact_email
                """,
                values,
            ).fetchone()

        if row is None:
            return None
        return VendorRecord(**dict(row))

    def list_facilities(self, vendor_id: int) -> list[Facility]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT f.id, f.code, f.name
                FROM facilities AS f
                JOIN vendor_facilities AS vf ON vf.facility_id = f.id
                WHERE vf.vendor_id = %s
                ORDER BY f.code, f.id
                """,
                (vendor_id,),
            ).fetchall()

        return [Facility(**dict(row)) for row in rows]
