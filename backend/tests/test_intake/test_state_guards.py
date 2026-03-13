import pytest
from arxi.modules.intake.models import RxStatus
from arxi.modules.intake.service import IntakeService


async def test_valid_transition_parsed_to_validated(db):
    """PARSED -> VALIDATED should succeed."""
    svc = IntakeService(db)
    rx = await _create_rx(svc, db)
    result = await svc.validate(rx.id, actor_id="worker")
    assert result.status == RxStatus.VALIDATED


async def test_valid_transition_validated_to_pending(db):
    """VALIDATED -> PENDING_REVIEW should succeed."""
    svc = IntakeService(db)
    rx = await _create_rx(svc, db)
    await svc.validate(rx.id, actor_id="worker")
    result = await svc.submit_for_review(rx.id, actor_id="worker")
    assert result.status == RxStatus.PENDING_REVIEW


async def test_invalid_approve_from_parsed(db):
    """PARSED -> APPROVED should be rejected."""
    svc = IntakeService(db)
    rx = await _create_rx(svc, db)
    with pytest.raises(ValueError, match="Invalid transition"):
        await svc.approve(rx.id, pharmacist_id="pharm1")


async def test_invalid_approve_from_validated(db):
    """VALIDATED -> APPROVED should be rejected (must be PENDING_REVIEW)."""
    svc = IntakeService(db)
    rx = await _create_rx(svc, db)
    await svc.validate(rx.id, actor_id="worker")
    with pytest.raises(ValueError, match="Invalid transition"):
        await svc.approve(rx.id, pharmacist_id="pharm1")


async def test_invalid_validate_from_approved(db):
    """APPROVED -> VALIDATED should be rejected."""
    svc = IntakeService(db)
    rx = await _create_rx(svc, db)
    await svc.validate(rx.id, actor_id="worker")
    await svc.submit_for_review(rx.id, actor_id="worker")
    await svc.approve(rx.id, pharmacist_id="pharm1")
    with pytest.raises(ValueError, match="Invalid transition"):
        await svc.validate(rx.id, actor_id="worker")


async def test_reject_from_pending_review(db):
    """PENDING_REVIEW -> REJECTED should succeed."""
    svc = IntakeService(db)
    rx = await _create_rx(svc, db)
    await svc.validate(rx.id, actor_id="worker")
    await svc.submit_for_review(rx.id, actor_id="worker")
    result = await svc.reject(rx.id, pharmacist_id="pharm1", notes="Bad sig")
    assert result.status == RxStatus.REJECTED


# --- Helpers ---

_MINIMAL_XML = """<?xml version="1.0"?>
<Message>
  <Header><MessageID>TEST-001</MessageID></Header>
  <Body><NewRx>
    <Patient><Name><FirstName>John</FirstName><LastName>Doe</LastName></Name><DateOfBirth>1990-01-15</DateOfBirth></Patient>
    <Prescriber><NPI>1234567890</NPI><DEANumber>AD1234567</DEANumber><Name><FirstName>Dr</FirstName><LastName>Smith</LastName></Name></Prescriber>
    <MedicationPrescribed>
      <DrugDescription>Amoxicillin 500mg Cap</DrugDescription>
      <NDC>00093310901</NDC>
      <Quantity>30</Quantity>
      <DaysSupply>10</DaysSupply>
      <Refills>2</Refills>
      <Sig>Take 1 capsule 3 times daily</Sig>
      <WrittenDate>2026-03-10</WrittenDate>
      <Substitutions>0</Substitutions>
    </MedicationPrescribed>
  </NewRx></Body>
</Message>"""


async def _create_rx(svc: IntakeService, db) -> "Prescription":
    return await svc.ingest_newrx(_MINIMAL_XML, source="e-prescribe", actor_id="test-agent")
