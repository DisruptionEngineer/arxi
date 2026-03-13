from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from arxi.auth.middleware import get_current_user, require_role
from arxi.auth.models import Role, User
from arxi.database import get_db
from arxi.modules.intake.clinical_review import ClinicalReviewService
from arxi.modules.intake.models import RxStatus
from arxi.modules.intake.schemas import (
    ManualRxRequest,
    PrescribeAssistRequest,
    PrescriptionOut,
    RxApproveRequest,
    RxQueueResponse,
    RxRejectRequest,
)
from arxi.modules.intake.service import IntakeService

router = APIRouter(prefix="/api/intake", tags=["intake"])


@router.post("/manual", response_model=PrescriptionOut)
async def create_manual_rx(
    req: ManualRxRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Manual prescription entry — walk-in, phone-in, transfer."""
    svc = IntakeService(db)
    try:
        rx = await svc.create_manual(req, actor_id=str(user.id), actor_role=user.role.value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return rx


@router.post("/newrx", response_model=PrescriptionOut)
async def ingest_newrx(
    xml_content: str = Body(..., media_type="text/plain"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = IntakeService(db)
    try:
        rx = await svc.ingest_newrx(xml_content, source="e-prescribe", actor_id=str(user.id))
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return rx


@router.get("/queue", response_model=RxQueueResponse)
async def get_queue(
    status: RxStatus | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = IntakeService(db)
    rxs, total = await svc.get_queue(status=status, limit=limit, offset=offset)
    return RxQueueResponse(prescriptions=rxs, total=total)


@router.get("/{rx_id}", response_model=PrescriptionOut)
async def get_prescription(
    rx_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = IntakeService(db)
    try:
        rx = await svc._get(rx_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return rx


@router.post("/{rx_id}/clinical-review")
async def run_clinical_review(
    rx_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.PHARMACIST)),
):
    """Run AI clinical decision support review (DUR + patient profile)."""
    svc = ClinicalReviewService(db)
    try:
        findings = await svc.run_review(
            rx_id,
            actor_id=str(user.id),
            actor_role=user.role.value,
            trigger="manual",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return findings


@router.post("/prescribe-assist")
async def prescribe_assist(
    req: PrescribeAssistRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.PHARMACIST)),
):
    """AI-assisted prescribing — generate Rx details from patient + drug selection."""
    svc = ClinicalReviewService(db)
    try:
        result = await svc.prescribe_assist(
            patient_id=req.patient_id,
            drug_id=req.drug_id,
            prescriber_npi=req.prescriber_npi,
            actor_id=str(user.id),
            actor_role=user.role.value,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result


@router.post("/{rx_id}/approve", response_model=PrescriptionOut)
async def approve_rx(
    rx_id: str,
    req: RxApproveRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.PHARMACIST)),
):
    svc = IntakeService(db)
    try:
        rx = await svc.approve(
            rx_id,
            pharmacist_id=str(user.id),
            pharmacist_name=user.full_name,
            notes=req.notes,
            clinical_checks=[c.value for c in req.clinical_checks] if req.clinical_checks else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return rx


@router.post("/{rx_id}/reject", response_model=PrescriptionOut)
async def reject_rx(
    rx_id: str,
    req: RxRejectRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(Role.PHARMACIST)),
):
    svc = IntakeService(db)
    try:
        rx = await svc.reject(
            rx_id,
            pharmacist_id=str(user.id),
            pharmacist_name=user.full_name,
            notes=req.notes,
            rejection_reason=req.rejection_reason.value,
            followup_action=req.followup_action.value,
            clinical_checks=[c.value for c in req.clinical_checks] if req.clinical_checks else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return rx
