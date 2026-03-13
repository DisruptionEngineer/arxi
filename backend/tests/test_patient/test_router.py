import pytest

from arxi.modules.patient.models import Patient
from arxi.modules.patient.service import PatientService


async def _seed_patient(db, **overrides) -> Patient:
    defaults = {
        "first_name": "John",
        "last_name": "Doe",
        "gender": "M",
        "date_of_birth": "1990-01-15",
    }
    defaults.update(overrides)
    svc = PatientService(db)
    return await svc.create(defaults)


async def test_list_patients(client, db):
    await _seed_patient(db)
    await _seed_patient(db, first_name="Jane", last_name="Smith")
    resp = await client.get("/api/patients")
    assert resp.status_code == 200
    body = resp.json()
    assert "patients" in body
    assert "total" in body
    assert body["total"] == 2


async def test_get_patient(client, db):
    patient = await _seed_patient(db)
    resp = await client.get(f"/api/patients/{patient.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == patient.id
    assert body["first_name"] == "John"


async def test_get_patient_not_found(client):
    resp = await client.get("/api/patients/nonexistent")
    assert resp.status_code == 404


async def test_get_patient_prescriptions(client, db):
    patient = await _seed_patient(db)
    resp = await client.get(f"/api/patients/{patient.id}/prescriptions")
    assert resp.status_code == 200
    body = resp.json()
    assert "prescriptions" in body
    assert isinstance(body["prescriptions"], list)
