from pydantic import BaseModel


class PatientResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    gender: str
    date_of_birth: str
    address_line1: str
    city: str
    state: str
    postal_code: str
    allergies: list | None = None
    conditions: list | None = None

    model_config = {"from_attributes": True}


class PatientListResponse(BaseModel):
    patients: list[PatientResponse]
    total: int


# --- Rx Context (patient-centric New Rx workflow) ---


class PrescriberSummary(BaseModel):
    npi: str
    name: str
    dea: str = ""
    rx_count: int
    last_rx_date: str


class RefillCandidate(BaseModel):
    drug_description: str
    ndc: str
    drug_id: str | None = None
    generic_name: str = ""
    strength: str = ""
    dosage_form: str = ""
    last_fill_date: str
    last_status: str
    remaining_refills: int
    prescriber_name: str
    prescriber_npi: str


class RxContextResponse(BaseModel):
    prescribers: list[PrescriberSummary]
    refill_candidates: list[RefillCandidate]
