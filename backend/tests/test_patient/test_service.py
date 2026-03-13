import pytest

from arxi.modules.patient.models import Patient
from arxi.modules.patient.service import PatientService


async def test_create_patient(db):
    svc = PatientService(db)
    patient = await svc.create({
        "first_name": "John",
        "last_name": "Doe",
        "gender": "M",
        "date_of_birth": "1990-01-15",
    })
    assert patient.id is not None
    assert patient.first_name == "John"
    assert patient.last_name == "Doe"
    assert patient.date_of_birth == "1990-01-15"


async def test_get_patient(db):
    svc = PatientService(db)
    created = await svc.create({
        "first_name": "Jane",
        "last_name": "Smith",
        "gender": "F",
        "date_of_birth": "1985-06-20",
    })
    fetched = await svc.get(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.first_name == "Jane"


async def test_get_patient_not_found(db):
    svc = PatientService(db)
    result = await svc.get("nonexistent-id")
    assert result is None


async def test_search_exact_match(db):
    svc = PatientService(db)
    await svc.create({
        "first_name": "Robert",
        "last_name": "Williams",
        "gender": "M",
        "date_of_birth": "1975-03-10",
    })
    results = await svc.search(
        last_name="Williams", first_name="Robert", dob="1975-03-10"
    )
    assert len(results) == 1
    assert results[0].first_name == "Robert"


async def test_search_no_match(db):
    svc = PatientService(db)
    results = await svc.search(
        last_name="Nobody", first_name="Here", dob="2000-01-01"
    )
    assert results == []


async def test_search_fuzzy_by_dob_and_prefix(db):
    svc = PatientService(db)
    await svc.create({
        "first_name": "Michael",
        "last_name": "Johnson",
        "gender": "M",
        "date_of_birth": "1988-12-01",
    })
    await svc.create({
        "first_name": "Michelle",
        "last_name": "Jones",
        "gender": "F",
        "date_of_birth": "1988-12-01",
    })
    results = await svc.search_fuzzy(dob="1988-12-01", last_name_prefix="joh")
    assert len(results) == 1
    assert results[0].last_name == "Johnson"


async def test_list_all_with_pagination(db):
    svc = PatientService(db)
    for i in range(5):
        await svc.create({
            "first_name": f"Patient{i}",
            "last_name": f"Test{i}",
            "gender": "M",
            "date_of_birth": "2000-01-01",
        })
    patients, total = await svc.list_all(limit=2, offset=0)
    assert total == 5
    assert len(patients) == 2

    patients2, total2 = await svc.list_all(limit=2, offset=2)
    assert total2 == 5
    assert len(patients2) == 2
