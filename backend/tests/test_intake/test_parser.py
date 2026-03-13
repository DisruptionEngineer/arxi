import pytest
from pathlib import Path
from arxi.modules.intake.parser import parse_newrx, ParsedRx

FIXTURE_DIR = Path(__file__).parent.parent.parent / "fixtures"


def test_parse_newrx_basic():
    xml_content = (FIXTURE_DIR / "sample_newrx.xml").read_text()
    result = parse_newrx(xml_content)
    assert isinstance(result, ParsedRx)
    assert result.patient.last_name == "Johnson"
    assert result.patient.first_name == "Maria"
    assert result.patient.gender == "F"
    assert result.patient.date_of_birth == "1984-09-09"
    assert result.prescriber.last_name == "Bless"
    assert result.prescriber.npi == "1939842031"
    assert result.prescriber.dea_number == "BB8027505"
    assert result.medication.drug_description == "Amoxicillin 500 MG Oral Capsule"
    assert result.medication.ndc == "00093310901"
    assert result.medication.quantity == 30
    assert result.medication.days_supply == 10
    assert result.medication.refills == 2
    assert "3 times daily" in result.medication.sig_text


def test_parse_newrx_invalid_xml():
    with pytest.raises(ValueError, match="Invalid NCPDP SCRIPT"):
        parse_newrx("<not><valid></valid></not>")
