"""Employee-facing read and meal selection workflow."""
from __future__ import annotations

from backend.core.errors import CodedHTTPException
from backend.repositories.employee_selection_repository import EmployeeSelectionRepository
from backend.repositories.menu_item_repository import MenuItemRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository, VendorRecord
from backend.schemas.employee import EmployeeMenuItem, EmployeeVendor, MealSelection, MealSelectionCreate
from backend.schemas.vendor_self import MenuItem as VendorMenuItem


class EmployeeOrderingService:
    def __init__(
        self,
        vendor_repository: VendorProfileRepository,
        menu_item_repository: MenuItemRepository,
        selection_repository: EmployeeSelectionRepository,
    ) -> None:
        self.vendor_repository = vendor_repository
        self.menu_item_repository = menu_item_repository
        self.selection_repository = selection_repository

    def list_vendors(self) -> list[EmployeeVendor]:
        return [self._vendor_to_schema(vendor) for vendor in self.vendor_repository.list(status="approved")]

    def get_vendor(self, vendor_id: int) -> EmployeeVendor:
        return self._vendor_to_schema(self._get_approved_vendor(vendor_id))

    def list_menu(
        self, vendor_id: int, *, category_id: int | None = None, available: bool | None = True
    ) -> list[EmployeeMenuItem]:
        self._get_approved_vendor(vendor_id)
        return [
            self._menu_item_to_schema(item)
            for item in self.menu_item_repository.list(
                vendor_id=vendor_id, category_id=category_id, available=available
            )
        ]

    def select_meal(
        self, employee_id: int, vendor_id: int, payload: MealSelectionCreate
    ) -> MealSelection:
        self._get_approved_vendor(vendor_id)
        item = self.menu_item_repository.get(vendor_id=vendor_id, item_id=payload.item_id)
        if item is None:
            raise CodedHTTPException(status_code=404, code="not_found", detail="menu item not found")
        if not item.available:
            raise CodedHTTPException(status_code=409, code="item_unavailable", detail="menu item unavailable")
        if item.daily_quota is not None and payload.quantity > item.daily_quota:
            raise CodedHTTPException(
                status_code=409,
                code="quantity_exceeds_daily_quota",
                detail="quantity exceeds daily quota",
            )

        return self.selection_repository.create(
            employee_id=employee_id,
            vendor_id=vendor_id,
            item_id=item.id,
            item_name=item.name,
            quantity=payload.quantity,
            unit_price_cents=item.price_cents,
        )

    def list_my_selections(self, employee_id: int) -> list[MealSelection]:
        return self.selection_repository.list(employee_id=employee_id)

    def _get_approved_vendor(self, vendor_id: int) -> VendorRecord:
        vendor = self.vendor_repository.get(vendor_id)
        if vendor is None or vendor.status != "approved":
            raise CodedHTTPException(status_code=404, code="not_found", detail="vendor not found")
        return vendor

    def _vendor_to_schema(self, vendor: VendorRecord) -> EmployeeVendor:
        return EmployeeVendor(
            id=vendor.id,
            name=vendor.name,
            address=vendor.address,
            business_hours=vendor.business_hours,
            contact_phone=vendor.contact_phone,
            contact_email=vendor.contact_email,
            served_facilities=self.vendor_repository.list_facilities(vendor.id),
        )

    @staticmethod
    def _menu_item_to_schema(item: VendorMenuItem) -> EmployeeMenuItem:
        return EmployeeMenuItem(
            id=item.id,
            vendor_id=item.vendor_id,
            category_id=item.category_id,
            name=item.name,
            description=item.description,
            price_cents=item.price_cents,
            available=item.available,
            daily_quota=item.daily_quota,
            photo_path=item.photo_path,
        )
