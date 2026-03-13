from arxi.agents.intake_agent import IntakeAgent


def test_validate_rx_structure():
    agent = IntakeAgent(ollama_url="http://localhost:11434", model="qwen3:8b-optimized")
    result = agent.validate_rx_fields({
        "patient_first_name": "Maria",
        "patient_last_name": "Johnson",
        "patient_dob": "1984-09-09",
        "drug_description": "Amoxicillin 500 MG Oral Capsule",
        "ndc": "00093310901",
        "quantity": 30,
        "days_supply": 10,
        "refills": 2,
        "sig_text": "Take 1 capsule by mouth 3 times daily",
        "prescriber_npi": "1939842031",
    })
    assert result["valid"] is True
    assert len(result["issues"]) == 0


def test_validate_rx_missing_fields():
    agent = IntakeAgent(ollama_url="http://localhost:11434", model="qwen3:8b-optimized")
    result = agent.validate_rx_fields({
        "patient_first_name": "",
        "drug_description": "Amoxicillin 500 MG",
        "ndc": "123",  # too short
        "quantity": 0,
        "sig_text": "",
    })
    assert result["valid"] is False
    assert len(result["issues"]) > 0
