from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from arxi.modules.drug.models import Drug
from arxi.modules.intake.models import Prescription
from arxi.modules.patient.models import Patient


class PatientService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> Patient:
        patient = Patient(
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            gender=data.get("gender", ""),
            date_of_birth=data.get("date_of_birth", ""),
            address_line1=data.get("address_line1", ""),
            city=data.get("city", ""),
            state=data.get("state", ""),
            postal_code=data.get("postal_code", ""),
        )
        self.db.add(patient)
        await self.db.flush()
        await self.db.commit()
        return patient

    async def get(self, patient_id: str) -> Patient | None:
        result = await self.db.execute(
            select(Patient).where(Patient.id == patient_id)
        )
        return result.scalar_one_or_none()

    async def search(
        self, *, last_name: str, first_name: str, dob: str
    ) -> list[Patient]:
        result = await self.db.execute(
            select(Patient).where(
                func.lower(Patient.last_name) == last_name.lower(),
                func.lower(Patient.first_name) == first_name.lower(),
                Patient.date_of_birth == dob,
            )
        )
        return list(result.scalars().all())

    async def search_fuzzy(
        self, *, dob: str, last_name_prefix: str
    ) -> list[Patient]:
        prefix = last_name_prefix.lower()
        result = await self.db.execute(
            select(Patient).where(
                Patient.date_of_birth == dob,
                func.lower(Patient.last_name).startswith(prefix),
            )
        )
        return list(result.scalars().all())

    async def list_all(
        self, *, limit: int = 50, offset: int = 0
    ) -> tuple[list[Patient], int]:
        count_stmt = select(func.count(Patient.id))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        data_stmt = (
            select(Patient)
            .order_by(Patient.last_name, Patient.first_name)
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(data_stmt)
        return list(result.scalars().all()), total

    async def get_rx_context(self, patient_id: str) -> dict:
        """Build Rx context for a patient: recent prescribers + refill candidates."""

        # --- Prescribers: group by (npi, name, dea), count, last date ---
        prescriber_stmt = (
            select(
                Prescription.prescriber_npi,
                Prescription.prescriber_name,
                Prescription.prescriber_dea,
                func.count(Prescription.id).label("rx_count"),
                func.max(Prescription.written_date).label("last_rx_date"),
            )
            .where(
                Prescription.patient_id == patient_id,
                Prescription.prescriber_npi != "",
            )
            .group_by(
                Prescription.prescriber_npi,
                Prescription.prescriber_name,
                Prescription.prescriber_dea,
            )
            .order_by(desc("last_rx_date"))
        )
        prescriber_rows = (await self.db.execute(prescriber_stmt)).all()

        prescribers = [
            {
                "npi": row.prescriber_npi,
                "name": row.prescriber_name,
                "dea": row.prescriber_dea or "",
                "rx_count": row.rx_count,
                "last_rx_date": row.last_rx_date or "",
            }
            for row in prescriber_rows
        ]

        # --- Refill candidates: most recent Rx per NDC via window function ---
        ranked = (
            select(
                Prescription.ndc,
                Prescription.drug_description,
                Prescription.written_date,
                Prescription.status,
                Prescription.refills,
                Prescription.prescriber_name,
                Prescription.prescriber_npi,
                func.row_number()
                    .over(
                        partition_by=Prescription.ndc,
                        order_by=desc(Prescription.written_date),
                    )
                    .label("rn"),
            )
            .where(
                Prescription.patient_id == patient_id,
                Prescription.ndc != "",
            )
            .subquery()
        )

        latest_stmt = (
            select(ranked).where(ranked.c.rn == 1).order_by(desc(ranked.c.written_date))
        )
        latest_rows = (await self.db.execute(latest_stmt)).all()

        # Match NDCs to drugs table for drug_id + metadata
        ndc_list = [row.ndc for row in latest_rows]
        drug_map: dict[str, Drug] = {}
        if ndc_list:
            drug_results = (
                await self.db.execute(select(Drug).where(Drug.ndc.in_(ndc_list)))
            ).scalars().all()
            drug_map = {d.ndc: d for d in drug_results}

        refill_candidates = []
        for row in latest_rows:
            drug = drug_map.get(row.ndc)
            status_val = row.status.value if hasattr(row.status, "value") else str(row.status)
            refill_candidates.append({
                "drug_description": row.drug_description,
                "ndc": row.ndc,
                "drug_id": drug.id if drug else None,
                "generic_name": drug.generic_name if drug else "",
                "strength": drug.strength if drug else "",
                "dosage_form": drug.dosage_form if drug else "",
                "last_fill_date": row.written_date or "",
                "last_status": status_val,
                "remaining_refills": row.refills or 0,
                "prescriber_name": row.prescriber_name,
                "prescriber_npi": row.prescriber_npi,
            })

        return {"prescribers": prescribers, "refill_candidates": refill_candidates}
