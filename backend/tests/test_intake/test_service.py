from pathlib import Path
from unittest.mock import AsyncMock, patch

from arxi.events import Event
from arxi.modules.intake.service import IntakeService
from arxi.modules.intake.models import RxStatus

FIXTURE_DIR = Path(__file__).parent.parent.parent / "fixtures"


async def test_ingest_newrx_xml(db):
    svc = IntakeService(db)
    xml = (FIXTURE_DIR / "sample_newrx.xml").read_text()
    rx = await svc.ingest_newrx(xml, source="e-prescribe", actor_id="system")
    assert rx.status == RxStatus.PARSED
    assert rx.patient_last_name == "Johnson"
    assert rx.drug_description == "Amoxicillin 500 MG Oral Capsule"
    assert rx.ndc == "00093310901"


async def test_rx_queue_status_progression(db):
    svc = IntakeService(db)
    xml = (FIXTURE_DIR / "sample_newrx.xml").read_text()
    rx = await svc.ingest_newrx(xml, source="e-prescribe", actor_id="system")
    assert rx.status == RxStatus.PARSED

    rx = await svc.validate(rx.id, actor_id="intake-agent")
    assert rx.status == RxStatus.VALIDATED

    rx = await svc.submit_for_review(rx.id, actor_id="intake-agent")
    assert rx.status == RxStatus.PENDING_REVIEW

    rx = await svc.approve(rx.id, pharmacist_id="rph-001")
    assert rx.status == RxStatus.APPROVED


async def test_approve_publishes_event(db):
    """IntakeService.approve should publish a prescription.status_changed event."""
    svc = IntakeService(db)
    xml = (FIXTURE_DIR / "sample_newrx.xml").read_text()
    rx = await svc.ingest_newrx(xml, source="e-prescribe", actor_id="system")
    await svc.validate(rx.id, actor_id="agent")
    await svc.submit_for_review(rx.id, actor_id="agent")

    with patch("arxi.modules.intake.service.event_bus") as mock_bus:
        mock_bus.publish = AsyncMock()
        await svc.approve(rx.id, pharmacist_id="rph-001", notes="ok")

        mock_bus.publish.assert_called_once()
        evt = mock_bus.publish.call_args[0][0]
        assert isinstance(evt, Event)
        assert evt.type == "prescription.status_changed"
        assert evt.data["status"] == "approved"


async def test_reject_publishes_event(db):
    """IntakeService.reject should publish a prescription.status_changed event."""
    svc = IntakeService(db)
    xml = (FIXTURE_DIR / "sample_newrx.xml").read_text()
    rx = await svc.ingest_newrx(xml, source="e-prescribe", actor_id="system")
    await svc.validate(rx.id, actor_id="agent")
    await svc.submit_for_review(rx.id, actor_id="agent")

    with patch("arxi.modules.intake.service.event_bus") as mock_bus:
        mock_bus.publish = AsyncMock()
        await svc.reject(rx.id, pharmacist_id="rph-001", notes="issue")

        mock_bus.publish.assert_called_once()
        evt = mock_bus.publish.call_args[0][0]
        assert evt.type == "prescription.status_changed"
        assert evt.data["status"] == "rejected"
