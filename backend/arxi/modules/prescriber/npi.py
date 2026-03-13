"""NPI validation and NPPES Registry lookup."""

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger("arxi.prescriber.npi")

NPPES_API_URL = "https://npiregistry.cms.hhs.gov/api/"
NPPES_TIMEOUT = 5.0


def validate_npi_format(npi: str) -> tuple[bool, str]:
    """Validate NPI format: 10 digits + Luhn-10 check digit.

    Returns (is_valid, message).
    """
    if not npi:
        return False, "NPI is required"

    cleaned = npi.strip().replace("-", "").replace(" ", "")

    if len(cleaned) != 10:
        return False, f"NPI must be 10 digits (got {len(cleaned)})"

    if not cleaned.isdigit():
        return False, "NPI must contain only digits"

    if cleaned[0] not in ("1", "2"):
        return False, "NPI must start with 1 (individual) or 2 (organization)"

    # Luhn-10 check digit with 80840 prefix.
    # The check digit sits at position 1 (rightmost) in the full 15-digit number,
    # so the rightmost digit of the 14-digit prefix is at position 2 (doubled).
    prefixed = "80840" + cleaned[:9]
    total = 0
    for i, ch in enumerate(prefixed):
        d = int(ch)
        # Double digits at even positions from the right in the full 15-digit number
        if (len(prefixed) - i) % 2 == 1:
            d *= 2
            if d > 9:
                d = d // 10 + d % 10
        total += d

    check_digit = (10 - (total % 10)) % 10
    if check_digit != int(cleaned[9]):
        return False, "Invalid NPI check digit (possible typo)"

    return True, "Valid NPI format"


@dataclass
class NPPESResult:
    """Result from NPPES Registry lookup."""
    found: bool
    npi: str
    name: str = ""
    credential: str = ""
    gender: str = ""
    enumeration_type: str = ""  # "NPI-1" (individual) or "NPI-2" (organization)
    specialty: str = ""
    address_city: str = ""
    address_state: str = ""
    status: str = ""  # "A" = active
    error: str = ""


async def lookup_nppes(npi: str) -> NPPESResult:
    """Look up an NPI in the NPPES Registry (free, no API key)."""
    valid, msg = validate_npi_format(npi)
    if not valid:
        return NPPESResult(found=False, npi=npi, error=msg)

    try:
        async with httpx.AsyncClient(timeout=NPPES_TIMEOUT) as client:
            resp = await client.get(
                NPPES_API_URL,
                params={
                    "number": npi,
                    "version": "2.1",
                },
            )

        if resp.status_code != 200:
            return NPPESResult(found=False, npi=npi, error=f"NPPES API returned {resp.status_code}")

        data = resp.json()
        result_count = data.get("result_count", 0)

        if result_count == 0:
            return NPPESResult(found=False, npi=npi, error="NPI not found in NPPES registry")

        result = data["results"][0]
        basic = result.get("basic", {})
        enum_type = result.get("enumeration_type", "")

        # Parse name
        if enum_type == "NPI-1":
            name = f"{basic.get('first_name', '')} {basic.get('last_name', '')}".strip()
        else:
            name = basic.get("organization_name", "")

        # Parse primary specialty
        taxonomies = result.get("taxonomies", [])
        primary_tax = next((t for t in taxonomies if t.get("primary")), taxonomies[0] if taxonomies else {})
        specialty = primary_tax.get("desc", "")

        # Parse primary address
        addresses = result.get("addresses", [])
        primary_addr = next((a for a in addresses if a.get("address_purpose") == "LOCATION"), addresses[0] if addresses else {})

        return NPPESResult(
            found=True,
            npi=npi,
            name=name,
            credential=basic.get("credential", ""),
            gender=basic.get("gender", ""),
            enumeration_type=enum_type,
            specialty=specialty,
            address_city=primary_addr.get("city", ""),
            address_state=primary_addr.get("state", ""),
            status=basic.get("status", ""),
        )

    except httpx.TimeoutException:
        logger.warning("NPPES lookup timeout for NPI %s", npi)
        return NPPESResult(found=False, npi=npi, error="NPPES lookup timed out")
    except Exception:
        logger.exception("NPPES lookup failed for NPI %s", npi)
        return NPPESResult(found=False, npi=npi, error="NPPES lookup failed")
