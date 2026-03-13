from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from arxi.auth.middleware import get_current_user, require_role
from arxi.auth.models import Role, User
from arxi.database import get_db
from arxi.modules.intake.models import Prescription
from arxi.modules.intake.schemas import PrescriptionOut
from arxi.modules.patient.schemas import (
    PatientListResponse,
    PatientResponse,
    RxContextResponse,
)
from arxi.modules.patient.service import PatientService

router = APIRouter(prefix="/api/patients", tags=["patients"])


@router.get("", response_model=PatientListResponse)
async def list_patients(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.PHARMACIST)),
):
    svc = PatientService(db)
    patients, total = await svc.list_all(limit=limit, offset=offset)
    return PatientListResponse(patients=patients, total=total)


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.PHARMACIST)),
):
    svc = PatientService(db)
    patient = await svc.get(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.get("/{patient_id}/prescriptions")
async def get_patient_prescriptions(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.PHARMACIST)),
):
    svc = PatientService(db)
    patient = await svc.get(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    result = await db.execute(
        select(Prescription).where(Prescription.patient_id == patient_id)
    )
    rxs = list(result.scalars().all())
    return {"prescriptions": [PrescriptionOut.model_validate(rx) for rx in rxs]}


@router.get("/{patient_id}/rx-context", response_model=RxContextResponse)
async def get_patient_rx_context(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.PHARMACIST)),
):
    """Patient's Rx context for New Rx workflow: prescribers + refill candidates."""
    svc = PatientService(db)
    patient = await svc.get(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    context = await svc.get_rx_context(patient_id)
    return context
