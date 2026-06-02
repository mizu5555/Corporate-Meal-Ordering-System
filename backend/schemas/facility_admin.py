from __future__ import annotations

from pydantic import BaseModel


class FacilityCreate(BaseModel):
    code: str
    name: str


class VendorFacilitiesUpdate(BaseModel):
    facility_ids: list[int]


class EmployeeFacilitiesUpdate(BaseModel):
    facility_ids: list[int]
