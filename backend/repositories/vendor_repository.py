"""Vendor application repository — Postgres-backed."""
from __future__ import annotations

from backend.db.connection import get_connection
from backend.schemas.vendor import VendorApplicationCreate, VendorApplicationDetail, VendorApplicationSummary


class VendorRepository:
    def create_application(self, user_id: int, data: VendorApplicationCreate) -> VendorApplicationDetail:
        with get_connection() as conn:
            vendor_row = conn.execute(
                """
                INSERT INTO vendors (name, status, address, business_hours, contact_phone, contact_email, owner_user_id)
                VALUES (%s, 'pending', %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (data.vendor_name, data.address, data.business_hours, data.contact_phone, data.contact_email, user_id),
            ).fetchone()
            vendor_id = vendor_row["id"]

            app_row = conn.execute(
                """
                INSERT INTO vendor_applications (vendor_id, submitted_by_user_id, status)
                VALUES (%s, %s, 'pending')
                RETURNING id, created_at
                """,
                (vendor_id, user_id),
            ).fetchone()

        return VendorApplicationDetail(
            application_id=app_row["id"],
            vendor_id=vendor_id,
            vendor_name=data.vendor_name,
            status="pending",
            address=data.address,
            business_hours=data.business_hours,
            contact_phone=data.contact_phone,
            contact_email=data.contact_email,
            submitted_at=app_row["created_at"],
        )

    def get_my_application(self, user_id: int) -> VendorApplicationDetail | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    va.id AS application_id,
                    va.status,
                    va.review_reason,
                    va.reviewed_at,
                    va.created_at AS submitted_at,
                    v.id AS vendor_id,
                    v.name AS vendor_name,
                    v.address,
                    v.business_hours,
                    v.contact_phone,
                    v.contact_email
                FROM vendor_applications va
                JOIN vendors v ON v.id = va.vendor_id
                WHERE va.submitted_by_user_id = %s
                ORDER BY va.id DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()

        if row is None:
            return None
        return VendorApplicationDetail(**dict(row))

    def list_applications(self, *, status: str | None = None) -> list[VendorApplicationSummary]:
        query = """
            SELECT
                va.id AS application_id,
                va.status,
                va.created_at AS submitted_at,
                v.id AS vendor_id,
                v.name AS vendor_name,
                u.email AS submitter_email,
                u.display_name AS submitter_name
            FROM vendor_applications va
            JOIN vendors v ON v.id = va.vendor_id
            LEFT JOIN users u ON u.id = va.submitted_by_user_id
        """
        params: list = []
        if status is not None:
            query += " WHERE va.status = %s"
            params.append(status)
        query += " ORDER BY va.id DESC"

        with get_connection() as conn:
            rows = conn.execute(query, params).fetchall()

        return [VendorApplicationSummary(**dict(row)) for row in rows]

    def get_application(self, application_id: int) -> VendorApplicationDetail | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    va.id AS application_id,
                    va.status,
                    va.review_reason,
                    va.reviewed_at,
                    va.created_at AS submitted_at,
                    v.id AS vendor_id,
                    v.name AS vendor_name,
                    v.address,
                    v.business_hours,
                    v.contact_phone,
                    v.contact_email,
                    u.email AS submitter_email,
                    u.display_name AS submitter_name
                FROM vendor_applications va
                JOIN vendors v ON v.id = va.vendor_id
                LEFT JOIN users u ON u.id = va.submitted_by_user_id
                WHERE va.id = %s
                """,
                (application_id,),
            ).fetchone()

        if row is None:
            return None
        return VendorApplicationDetail(**dict(row))

    def mark_application_reviewed(
        self,
        application_id: int,
        decision: str,
        reviewer_user_id: int | None = None,
        reason: str | None = None,
    ) -> None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT vendor_id FROM vendor_applications WHERE id = %s",
                (application_id,),
            ).fetchone()
            if row is None:
                return

            vendor_id = row["vendor_id"]
            vendor_status = "approved" if decision == "approved" else "rejected"

            conn.execute(
                """
                UPDATE vendor_applications
                SET status = %s,
                    review_reason = %s,
                    reviewed_by_user_id = %s,
                    reviewed_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s
                """,
                (decision, reason, reviewer_user_id, application_id),
            )
            conn.execute(
                "UPDATE vendors SET status = %s, updated_at = NOW() WHERE id = %s",
                (vendor_status, vendor_id),
            )
