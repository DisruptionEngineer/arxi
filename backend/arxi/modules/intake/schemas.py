from datetime import datetime

from pydantic import BaseModel

from arxi.modules.intake.models import (
    ClinicalCheck,
    FollowupAction,
    RejectionReason,
    RxStatus,
)


class PrescriptionOut(BaseModel):
    id: str
    status: RxStatus
    source: str
    patient_id: str | None = None
    patient_first_name: str
    patient_last_name: str
    patient_dob: str
    prescriber_name: str
    prescriber_npi: str = ""
    prescriber_dea: str = ""
    drug_description: str
    ndc: str
    quantity: int
    days_supply: int
    refills: int
    sig_text: str
    written_date: str
    substitutions: int = 0
    created_at: datetime
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_notes: str | None = None
    rejection_reason: str | None = None
    followup_action: str | None = None
    clinical_checks: list[str] | None = None
    reviewer_name: str | None = None
    clinical_findings: dict | None = None

    model_config = {"from_attributes": True}


class ManualRxRequest(BaseModel):
    """Manual prescription entry — walk-in, phone-in, or transfer."""
    patient_first_name: str
    patient_last_name: str
    patient_dob: str  # YYYY-MM-DD

    prescriber_name: str
    prescriber_npi: str = ""
    prescriber_dea: str = ""

    drug_description: str
    ndc: str = ""
    quantity: int
    days_supply: int
    refills: int = 0
    sig_text: str
    written_date: str = ""  # YYYY-MM-DD, defaults to today
    substitutions: int = 0


class RxApproveRequest(BaseModel):
    pharmacist_id: str
    notes: str | None = None
    clinical_checks: list[ClinicalCheck] = []


class RxRejectRequest(BaseModel):
    pharmacist_id: str
    rejection_reason: RejectionReason
    followup_action: FollowupAction
    notes: str
    clinical_checks: list[ClinicalCheck] = []


class RxCorrectRequest(BaseModel):
    pharmacist_id: str
    corrections: dict
    notes: str | None = None


class RxQueueResponse(BaseModel):
    prescriptions: list[PrescriptionOut]
    total: int


class PrescribeAssistRequest(BaseModel):
    patient_id: str
    drug_id: str
    prescriber_npi: str


class PrescribeAssistResponse(BaseModel):
    drug_description: str
    ndc: str
    rx_classification: str | None = None
    classification_reasoning: str | None = None
    quantity: int | None = None
    days_supply: int | None = None
    refills: int | None = None
    sig_text: str | None = None
    substitutions: int = 0
    reasoning: str | None = None
    _thinking: str | None = None
    _model: str | None = None
    _generated_at: str | None = None
    _eval_duration_ms: int | None = None
