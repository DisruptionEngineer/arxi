from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from arxi.auth.models import Role
from arxi.events import Event, event_bus
from arxi.modules.compliance.service import AuditService
from arxi.modules.intake.models import Prescription, RxStatus
from arxi.modules.intake.parser import parse_newrx
from arxi.modules.intake.schemas import ManualRxRequest
from arxi.modules.patient.matcher import PatientMatcher


class IntakeService:
    VALID_TRANSITIONS: dict[RxStatus, set[RxStatus]] = {
        RxStatus.RECEIVED: {RxStatus.PARSED},
        RxStatus.PARSED: {RxStatus.VALIDATED},
        RxStatus.VALIDATED: {RxStatus.PENDING_REVIEW},
        RxStatus.PENDING_REVIEW: {RxStatus.APPROVED, RxStatus.REJECTED},
        RxStatus.REJECTED: {RxStatus.CORRECTED},
        RxStatus.CORRECTED: {RxStatus.PENDING_REVIEW},
        RxStatus.APPROVED: set(),  # terminal
    }

    def _check_transition(self, rx: Prescription, target: RxStatus) -> None:
        allowed = self.VALID_TRANSITIONS.get(rx.status, set())
        if target not in allowed:
            raise ValueError(
                f"Invalid transition: {rx.status.value} \u2192 {target.value} "
                f"(allowed: {', '.join(s.value for s in allowed) or 'none'})"
            )

    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit = AuditService(db)

    async def create_manual(
        self, req: ManualRxRequest, *, actor_id: str, actor_role: str
    ) -> Prescription:
        """Manual Rx entry — phone-in, walk-in, transfer. Goes straight to pending_review."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        rx = Prescription(
            source="manual",
            status=RxStatus.PENDING_REVIEW,
            patient_first_name=req.patient_first_name.strip(),
            patient_last_name=req.patient_last_name.strip(),
            patient_dob=req.patient_dob,
            prescriber_name=req.prescriber_name.strip(),
            prescriber_npi=req.prescriber_npi.strip(),
            prescriber_dea=req.prescriber_dea.strip(),
            drug_description=req.drug_description.strip(),
            ndc=req.ndc.strip(),
            quantity=req.quantity,
            days_supply=req.days_supply,
            refills=req.refills,
            sig_text=req.sig_text.strip(),
            written_date=req.written_date or today,
            substitutions=req.substitutions,
        )
        self.db.add(rx)
        await self.db.flush()
        await self.audit.log(
            action="prescription.manual_create",
            actor_id=actor_id,
            actor_role=actor_role,
            resource_type="prescription",
            resource_id=rx.id,
            detail={
                "source": "manual",
                "drug": req.drug_description,
                "patient": f"{req.patient_last_name}, {req.patient_first_name}",
            },
            before_state=None,
            after_state={"status": "pending_review"},
        )
        await self.db.commit()

        # Patient matching — link or auto-create patient record
        try:
            matcher = PatientMatcher(self.db)
            match_result = await matcher.match_and_link(rx)
            await self.audit.log(
                action=f"patient.{match_result.outcome.replace('linked', 'link')}",
                actor_id=actor_id,
                actor_role=actor_role,
                resource_type="prescription",
                resource_id=rx.id,
                detail={
                    "patient_id": match_result.patient_id,
                    "tier": match_result.tier,
                    "confidence": match_result.confidence,
                    "detail": match_result.detail,
                },
            )
            await self.db.commit()
        except Exception:
            import logging
            logging.getLogger("arxi.intake").exception(
                "Patient matching failed for manual rx %s", rx.id[:8]
            )

        await event_bus.publish(Event(
            type="prescription.status_changed",
            resource_id=rx.id,
            data={
                "status": "pending_review",
                "patient_name": f"{rx.patient_first_name} {rx.patient_last_name}",
                "drug_description": rx.drug_description,
            },
            actor_id=actor_id,
        ))
        return rx

    async def ingest_newrx(
        self, xml_content: str, *, source: str, actor_id: str
    ) -> Prescription:
        parsed = parse_newrx(xml_content)
        rx = Prescription(
            source=source,
            message_id=parsed.message_id,
            raw_xml=xml_content,
            status=RxStatus.PARSED,
            patient_first_name=parsed.patient.first_name,
            patient_last_name=parsed.patient.last_name,
            patient_dob=parsed.patient.date_of_birth,
            prescriber_npi=parsed.prescriber.npi,
            prescriber_dea=parsed.prescriber.dea_number,
            prescriber_name=f"{parsed.prescriber.first_name} {parsed.prescriber.last_name}",
            drug_description=parsed.medication.drug_description,
            ndc=parsed.medication.ndc,
            quantity=parsed.medication.quantity,
            days_supply=parsed.medication.days_supply,
            refills=parsed.medication.refills,
            sig_text=parsed.medication.sig_text,
            written_date=parsed.medication.written_date,
            substitutions=parsed.medication.substitutions,
        )
        self.db.add(rx)
        await self.db.flush()
        await self.audit.log(
            action="prescription.create",
            actor_id=actor_id,
            actor_role=Role.AGENT.value,
            resource_type="prescription",
            resource_id=rx.id,
            detail={"source": source, "ndc": rx.ndc},
            before_state=None,
            after_state={"status": "parsed"},
        )
        await self.db.commit()
        return rx

    async def validate(self, rx_id: str, *, actor_id: str) -> Prescription:
        rx = await self._get(rx_id)
        self._check_transition(rx, RxStatus.VALIDATED)
        old_status = rx.status.value
        rx.status = RxStatus.VALIDATED
        await self.audit.log(
            action="prescription.validate",
            actor_id=actor_id,
            actor_role=Role.AGENT.value,
            resource_type="prescription",
            resource_id=rx_id,
            before_state={"status": old_status},
            after_state={"status": "validated"},
        )
        await self.db.commit()
        return rx

    async def submit_for_review(self, rx_id: str, *, actor_id: str) -> Prescription:
        rx = await self._get(rx_id)
        self._check_transition(rx, RxStatus.PENDING_REVIEW)
        old_status = rx.status.value
        rx.status = RxStatus.PENDING_REVIEW
        await self.audit.log(
            action="prescription.submit_review",
            actor_id=actor_id,
            actor_role=Role.AGENT.value,
            resource_type="prescription",
            resource_id=rx_id,
            before_state={"status": old_status},
            after_state={"status": "pending_review"},
        )
        await self.db.commit()
        return rx

    async def approve(
        self,
        rx_id: str,
        *,
        pharmacist_id: str,
        pharmacist_name: str,
        notes: str | None = None,
        clinical_checks: list[str] | None = None,
    ) -> Prescription:
        rx = await self._get(rx_id)
        self._check_transition(rx, RxStatus.APPROVED)
        old_status = rx.status.value
        rx.status = RxStatus.APPROVED
        rx.reviewed_by = pharmacist_id
        rx.reviewed_at = datetime.now(timezone.utc)
        rx.review_notes = notes
        rx.clinical_checks = clinical_checks or None
        rx.reviewer_name = pharmacist_name
        # Build clinical findings summary for audit trail
        cds_summary = None
        if rx.clinical_findings:
            flagged_cats = [
                cat for cat in ["dur_review", "drug_interactions", "allergy_screening",
                                "dose_range", "patient_profile", "prescriber_credentials"]
                if rx.clinical_findings.get(cat, {}).get("status") == "flagged"
            ]
            cds_summary = {
                "overall_risk": rx.clinical_findings.get("overall_risk"),
                "flagged_categories": flagged_cats,
            }

        await self.audit.log(
            action="prescription.approve",
            actor_id=pharmacist_id,
            actor_role=Role.PHARMACIST.value,
            resource_type="prescription",
            resource_id=rx_id,
            detail={
                "notes": notes,
                "clinical_checks": clinical_checks,
                "clinical_findings_summary": cds_summary,
            },
            before_state={"status": old_status},
            after_state={"status": "approved"},
        )
        await self.db.commit()
        await event_bus.publish(Event(
            type="prescription.status_changed",
            resource_id=rx_id,
            data={
                "status": "approved",
                "patient_name": f"{rx.patient_first_name} {rx.patient_last_name}",
                "drug_description": rx.drug_description,
            },
            actor_id=pharmacist_id,
        ))
        return rx

    async def reject(
        self,
        rx_id: str,
        *,
        pharmacist_id: str,
        pharmacist_name: str,
        notes: str,
        rejection_reason: str,
        followup_action: str,
        clinical_checks: list[str] | None = None,
    ) -> Prescription:
        rx = await self._get(rx_id)
        self._check_transition(rx, RxStatus.REJECTED)
        old_status = rx.status.value
        rx.status = RxStatus.REJECTED
        rx.reviewed_by = pharmacist_id
        rx.reviewed_at = datetime.now(timezone.utc)
        rx.review_notes = notes
        rx.rejection_reason = rejection_reason
        rx.followup_action = followup_action
        rx.clinical_checks = clinical_checks or None
        rx.reviewer_name = pharmacist_name
        # Build clinical findings summary for audit trail
        cds_summary = None
        if rx.clinical_findings:
            flagged_cats = [
                cat for cat in ["dur_review", "drug_interactions", "allergy_screening",
                                "dose_range", "patient_profile", "prescriber_credentials"]
                if rx.clinical_findings.get(cat, {}).get("status") == "flagged"
            ]
            cds_summary = {
                "overall_risk": rx.clinical_findings.get("overall_risk"),
                "flagged_categories": flagged_cats,
            }

        await self.audit.log(
            action="prescription.reject",
            actor_id=pharmacist_id,
            actor_role=Role.PHARMACIST.value,
            resource_type="prescription",
            resource_id=rx_id,
            detail={
                "notes": notes,
                "rejection_reason": rejection_reason,
                "followup_action": followup_action,
                "clinical_checks": clinical_checks,
                "clinical_findings_summary": cds_summary,
            },
            before_state={"status": old_status},
            after_state={"status": "rejected"},
        )
        await self.db.commit()
        await event_bus.publish(Event(
            type="prescription.status_changed",
            resource_id=rx_id,
            data={
                "status": "rejected",
                "patient_name": f"{rx.patient_first_name} {rx.patient_last_name}",
                "drug_description": rx.drug_description,
            },
            actor_id=pharmacist_id,
        ))
        return rx

    async def get_queue(
        self, *, status: RxStatus | None = None, limit: int = 50, offset: int = 0
    ) -> tuple[list[Prescription], int]:
        stmt = (
            select(Prescription)
            .order_by(Prescription.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status:
            stmt = stmt.where(Prescription.status == status)
        result = await self.db.execute(stmt)
        rxs = list(result.scalars().all())

        count_stmt = select(func.count(Prescription.id))
        if status:
            count_stmt = count_stmt.where(Prescription.status == status)
        total = (await self.db.execute(count_stmt)).scalar() or 0

        return rxs, total

    async def _get(self, rx_id: str) -> Prescription:
        result = await self.db.execute(
            select(Prescription).where(Prescription.id == rx_id)
        )
        rx = result.scalar_one_or_none()
        if not rx:
            raise ValueError(f"Prescription {rx_id} not found")
        return rx
