"""Polling pipeline worker. Finds PARSED prescriptions, validates, submits for review."""

import asyncio
import logging
import signal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from arxi.agents.intake_agent import IntakeAgent
from arxi.config import settings
from arxi.database import async_session
from arxi.events import Event, event_bus
from arxi.modules.intake.clinical_review import ClinicalReviewService
from arxi.modules.intake.models import Prescription, RxStatus
from arxi.modules.compliance.service import AuditService
from arxi.modules.intake.service import IntakeService
from arxi.modules.patient.matcher import PatientMatcher

logger = logging.getLogger("arxi.worker")

POLL_INTERVAL = 5  # seconds
WORKER_ACTOR_ID = "pipeline-worker"


async def process_pending(db: AsyncSession) -> int:
    """Process all PARSED prescriptions. Returns count processed."""
    result = await db.execute(
        select(Prescription).where(Prescription.status == RxStatus.PARSED)
    )
    pending = list(result.scalars().all())

    if not pending:
        return 0

    svc = IntakeService(db)
    agent = IntakeAgent(ollama_url=settings.ollama_url, model=settings.ollama_model)
    processed = 0

    for rx in pending:
        try:
            # Step 1: Rule-based validation
            rx_data = {
                "patient_first_name": rx.patient_first_name,
                "patient_last_name": rx.patient_last_name,
                "drug_description": rx.drug_description,
                "ndc": rx.ndc,
                "quantity": rx.quantity,
                "sig_text": rx.sig_text,
                "refills": rx.refills,
            }
            validation = agent.validate_rx_fields(rx_data)

            # Step 2: Transition PARSED -> VALIDATED
            await svc.validate(rx.id, actor_id=WORKER_ACTOR_ID)

            # Step 2.5: Patient matching
            try:
                matcher = PatientMatcher(db)
                match_result = await matcher.match_and_link(rx)
                audit = AuditService(db)
                await audit.log(
                    action=f"patient.{match_result.outcome.replace('linked', 'link')}",
                    actor_id=WORKER_ACTOR_ID,
                    actor_role="agent",
                    resource_type="prescription",
                    resource_id=rx.id,
                    detail={
                        "patient_id": match_result.patient_id,
                        "tier": match_result.tier,
                        "confidence": match_result.confidence,
                        "detail": match_result.detail,
                    },
                )
                await db.commit()
                logger.info(
                    "Patient match for rx %s: %s (tier %d, %s)",
                    rx.id[:8],
                    match_result.outcome,
                    match_result.tier,
                    match_result.detail,
                )
            except Exception:
                logger.exception("Patient matching failed for rx %s", rx.id[:8])

            # Step 3: Transition VALIDATED -> PENDING_REVIEW
            await svc.submit_for_review(rx.id, actor_id=WORKER_ACTOR_ID)

            # Step 3.5: Clinical Decision Support — automated DUR + patient profile review
            try:
                clinical_svc = ClinicalReviewService(db)
                findings = await clinical_svc.run_review(
                    rx.id,
                    actor_id=WORKER_ACTOR_ID,
                    actor_role="agent",
                    trigger="pipeline",
                )
                logger.info(
                    "Clinical review for rx %s: risk=%s",
                    rx.id[:8],
                    findings.get("overall_risk", "?"),
                )
            except Exception:
                logger.exception(
                    "Clinical review failed for rx %s — pharmacist can trigger manually",
                    rx.id[:8],
                )

            # Publish status change event
            await event_bus.publish(Event(
                type="prescription.status_changed",
                resource_id=rx.id,
                data={
                    "status": "pending_review",
                    "patient_name": f"{rx.patient_first_name} {rx.patient_last_name}",
                    "drug_description": rx.drug_description,
                },
                actor_id=WORKER_ACTOR_ID,
            ))

            # Step 4: Attach validation issues as review notes (if any)
            if not validation["valid"]:
                refreshed = await svc._get(rx.id)
                refreshed.review_notes = "Validation issues:\n" + "\n".join(
                    f"- {issue}" for issue in validation["issues"]
                )
                await db.commit()

            processed += 1
            logger.info(
                "Processed rx %s -> PENDING_REVIEW (valid=%s)",
                rx.id[:8],
                validation["valid"],
            )

        except Exception:
            logger.exception("Failed to process rx %s", rx.id[:8])
            await db.rollback()

    return processed


async def run_worker() -> None:
    """Main polling loop."""
    logger.info("Pipeline worker started (poll every %ds)", POLL_INTERVAL)
    running = True

    def _stop(sig, frame):
        nonlocal running
        logger.info("Received signal %s, shutting down...", sig)
        running = False

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    while running:
        try:
            async with async_session() as db:
                count = await process_pending(db)
                if count:
                    logger.info("Processed %d prescription(s)", count)
        except Exception:
            logger.exception("Worker loop error")

        await asyncio.sleep(POLL_INTERVAL)

    logger.info("Pipeline worker stopped")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    asyncio.run(run_worker())
