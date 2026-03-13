import defusedxml.ElementTree as ET
from dataclasses import dataclass


@dataclass
class ParsedPatient:
    first_name: str
    last_name: str
    gender: str
    date_of_birth: str
    address_line1: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""


@dataclass
class ParsedPrescriber:
    first_name: str
    last_name: str
    npi: str
    dea_number: str = ""


@dataclass
class ParsedMedication:
    drug_description: str
    ndc: str
    quantity: int
    days_supply: int
    refills: int
    sig_text: str
    written_date: str
    substitutions: int = 0


@dataclass
class ParsedRx:
    message_id: str
    patient: ParsedPatient
    prescriber: ParsedPrescriber
    medication: ParsedMedication


def _text(el: ET.Element | None, path: str, default: str = "") -> str:
    if el is None:
        return default
    node = el.find(path)
    return node.text.strip() if node is not None and node.text else default


def parse_newrx(xml_content: str) -> ParsedRx:
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        raise ValueError(f"Invalid NCPDP SCRIPT XML: {e}")

    body = root.find("Body")
    if body is None:
        raise ValueError("Invalid NCPDP SCRIPT: missing Body element")
    newrx = body.find("NewRx")
    if newrx is None:
        raise ValueError("Invalid NCPDP SCRIPT: missing NewRx element")

    # Parse header
    header = root.find("Header")
    message_id = _text(header, "MessageID", "UNKNOWN")

    # Parse patient
    hp = newrx.find("Patient/HumanPatient")
    patient = ParsedPatient(
        first_name=_text(hp, "Name/FirstName"),
        last_name=_text(hp, "Name/LastName"),
        gender=_text(hp, "Gender"),
        date_of_birth=_text(hp, "DateOfBirth/Date"),
        address_line1=_text(hp, "Address/AddressLine1"),
        city=_text(hp, "Address/City"),
        state=_text(hp, "Address/StateProvince"),
        postal_code=_text(hp, "Address/PostalCode"),
    )

    # Parse prescriber
    nv = newrx.find("Prescriber/NonVeterinarian")
    prescriber = ParsedPrescriber(
        first_name=_text(nv, "Name/FirstName"),
        last_name=_text(nv, "Name/LastName"),
        npi=_text(nv, "Identification/NPI"),
        dea_number=_text(nv, "Identification/DEANumber"),
    )

    # Parse medication
    med = newrx.find("MedicationPrescribed")
    medication = ParsedMedication(
        drug_description=_text(med, "DrugDescription"),
        ndc=_text(med, "DrugCoded/ProductCode/Code"),
        quantity=int(_text(med, "Quantity/Value", "0")),
        days_supply=int(_text(med, "DaysSupply", "0")),
        refills=int(_text(med, "NumberOfRefills", "0")),
        sig_text=_text(med, "Sig/SigText"),
        written_date=_text(med, "WrittenDate/Date"),
        substitutions=int(_text(med, "Substitutions", "0")),
    )

    return ParsedRx(
        message_id=message_id,
        patient=patient,
        prescriber=prescriber,
        medication=medication,
    )
