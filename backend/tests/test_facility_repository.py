from backend.repositories.facility_repository import FacilityRepository


def test_create_is_idempotent_on_code():
    repo = FacilityRepository()
    a = repo.create_facility("F99", "Fab 99")
    b = repo.create_facility("F99", "Fab 99 dup")
    assert a.id == b.id
    assert any(f.code == "F99" for f in repo.list_facilities())


def test_set_and_get_vendor_facilities():
    repo = FacilityRepository()
    f1 = repo.create_facility("F1", "One")
    f2 = repo.create_facility("F2", "Two")
    repo.set_vendor_facilities(7, [f1.id, f2.id])
    assert sorted(repo.get_vendor_facility_ids(7)) == sorted([f1.id, f2.id])
    repo.set_vendor_facilities(7, [f1.id])
    assert repo.get_vendor_facility_ids(7) == [f1.id]


def test_facility_exists():
    repo = FacilityRepository()
    f = repo.create_facility("F1", "One")
    assert repo.facility_exists(f.id)
    assert not repo.facility_exists(99999)
