import pytest
from unittest.mock import AsyncMock, patch

from arxi.events import Event
from arxi.modules.compliance.service import AuditService
from arxi.modules.intake.models import RxStatus
from arxi.modules.intake.service import IntakeService
from arxi.modules.patient.service import PatientService
from arxi.worker import process_pending

# Re-use the XML fixture from test_state_guards
from tests.test_intake.test_state_guards import _MINIMAL_XML


async def test_process_pending_validates_and_submits(db):
    """Worker should move PARSED -> VALIDATED -> PENDING_REVIEW."""
    svc = IntakeService(db)
    rx = await svc.ingest_newrx(_MINIMAL_XML, source="e-prescribe", actor_id="test-agent")
    assert rx.status == RxStatus.PARSED

    processed = await process_pending(db)
    assert processed == 1

    # Re-fetch to check final status
    updated = await svc._get(rx.id)
    assert updated.status == RxStatus.PENDING_REVIEW


async def test_process_pending_skips_non_parsed(db):
    """Worker should only touch PARSED prescriptions."""
    svc = IntakeService(db)
    rx = await svc.ingest_newrx(_MINIMAL_XML, source="e-prescribe", actor_id="test-agent")
    # Advance past PARSED manually
    await svc.validate(rx.id, actor_id="worker")
    await svc.submit_for_review(rx.id, actor_id="worker")

    processed = await process_pending(db)
    assert processed == 0


async def test_process_pending_no_prescriptions(db):
    """Worker should handle empty queue gracefully."""
    processed = await process_pending(db)
    assert processed == 0


async def test_process_pending_attaches_validation_issues(db):
    """If validation finds issues, they should appear in review_notes."""
    svc = IntakeService(db)
    # Create rx with good data first
    rx = await svc.ingest_newrx(_MINIMAL_XML, source="e-prescribe", actor_id="test-agent")
    # Manually corrupt the NDC to trigger validation failure
    rx.ndc = "123"
    await db.commit()

    await process_pending(db)

    updated = await svc._get(rx.id)
    assert updated.status == RxStatus.PENDING_REVIEW
    assert updated.review_notes is not None
    assert "NDC" in updated.review_notes


async def test_worker_publishes_status_changed_event(db):
    """Worker should publish prescription.status_changed after submitting for review."""
    svc = IntakeService(db)
    rx = await svc.ingest_newrx(_MINIMAL_XML, source="e-prescribe", actor_id="test-agent")

    with (
        patch("arxi.worker.event_bus") as mock_bus,
        patch("arxi.modules.patient.matcher.event_bus", new=AsyncMock()),
    ):
        mock_bus.publish = AsyncMock()
        await process_pending(db)

        mock_bus.publish.assert_called_once()
        evt = mock_bus.publish.call_args[0][0]
        assert isinstance(evt, Event)
        assert evt.type == "prescription.status_changed"
        assert evt.data["status"] == "pending_review"
        assert evt.actor_id == "pipeline-worker"


async def test_worker_matches_patient_during_processing(db):
    """Worker should run patient matching and set patient_id on the Rx."""
    svc = IntakeService(db)
    rx = await svc.ingest_newrx(_MINIMAL_XML, source="e-prescribe", actor_id="test-agent")
    assert rx.patient_id is None

    with patch("arxi.modules.patient.matcher.event_bus", new=AsyncMock()):
        await process_pending(db)

    updated = await svc._get(rx.id)
    assert updated.status == RxStatus.PENDING_REVIEW
    assert updated.patient_id is not None

    patient_svc = PatientService(db)
    patient = await patient_svc.get(updated.patient_id)
    assert patient is not None


async def test_worker_continues_on_matching_failure(db):
    """If patient matching fails, Rx should still reach PENDING_REVIEW."""
    svc = IntakeService(db)
    rx = await svc.ingest_newrx(_MINIMAL_XML, source="e-prescribe", actor_id="test-agent")

    with patch("arxi.worker.PatientMatcher") as MockMatcher:
        mock_instance = AsyncMock()
        mock_instance.match_and_link = AsyncMock(side_effect=Exception("matcher boom"))
        MockMatcher.return_value = mock_instance
        await process_pending(db)

    updated = await svc._get(rx.id)
    assert updated.status == RxStatus.PENDING_REVIEW
    assert updated.patient_id is None


async def test_worker_audit_logs_patient_match(db):
    """Worker should create audit log entry for patient matching."""
    svc = IntakeService(db)
    rx = await svc.ingest_newrx(_MINIMAL_XML, source="e-prescribe", actor_id="test-agent")

    with patch("arxi.modules.patient.matcher.event_bus", new=AsyncMock()):
        await process_pending(db)

    audit_svc = AuditService(db)
    logs = await audit_svc.query(resource_id=rx.id)
    actions = [log.action for log in logs]
    assert any(a in ("patient.created", "patient.link") for a in actions)
