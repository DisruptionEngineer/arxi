from fastapi import APIRouter, Depends
from pydantic import BaseModel

from arxi.auth.middleware import get_current_user
from arxi.auth.models import User
from arxi.modules.prescriber.npi import NPPESResult, lookup_nppes, validate_npi_format

router = APIRouter(prefix="/api/prescribers", tags=["prescribers"])


class NPIValidationResponse(BaseModel):
    valid: bool
    message: str
    npi: str
    # NPPES lookup fields (populated if valid and found)
    found: bool = False
    name: str = ""
    credential: str = ""
    gender: str = ""
    enumeration_type: str = ""
    specialty: str = ""
    address_city: str = ""
    address_state: str = ""
    status: str = ""


@router.get("/validate-npi/{npi}", response_model=NPIValidationResponse)
async def validate_npi(
    npi: str,
    user: User = Depends(get_current_user),
):
    """Validate NPI format (Luhn-10) and look up in NPPES Registry."""
    valid, message = validate_npi_format(npi)

    if not valid:
        return NPIValidationResponse(valid=False, message=message, npi=npi)

    # Format is valid — do NPPES lookup
    result: NPPESResult = await lookup_nppes(npi)

    return NPIValidationResponse(
        valid=True,
        message="Valid NPI" + (f" — {result.name}" if result.found else " (not found in NPPES)"),
        npi=npi,
        found=result.found,
        name=result.name,
        credential=result.credential,
        gender=result.gender,
        enumeration_type=result.enumeration_type,
        specialty=result.specialty,
        address_city=result.address_city,
        address_state=result.address_state,
        status=result.status,
    )
