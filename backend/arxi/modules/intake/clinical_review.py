"""Clinical Decision Support — AI-powered DUR + patient profile review via Ollama."""

import json
import logging
import re
import time
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from arxi.config import settings
from arxi.modules.compliance.service import AuditService
from arxi.modules.drug.models import Drug
from arxi.modules.intake.models import Prescription, RxStatus
from arxi.modules.patient.models import Patient

logger = logging.getLogger("arxi.clinical_review")

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

CDS_SYSTEM_PROMPT = """You are a senior clinical pharmacist performing a comprehensive Drug Utilization Review (DUR) and patient profile review. Analyze the prescription data provided and return a structured JSON assessment.

For each category, evaluate and return:
- "status": "flagged" if concerns found, "clear" if no concerns
- "findings": array of finding objects (empty array if clear)

Each finding object:
{
  "type": "duplicate_therapy" | "drug_interaction" | "allergy_risk" | "dose_concern" | "age_consideration" | "condition_contraindication" | "credential_issue" | "other",
  "severity": "high" | "moderate" | "low",
  "description": "Concise clinical description of the concern",
  "recommendation": "Specific actionable recommendation"
}

Evaluate these 6 categories:
1. dur_review — Duplicate therapy, therapeutic overlap, recent fills
2. drug_interactions — Drug-drug interactions with active medications
3. allergy_screening — Cross-reactivity, documented allergy conflicts
4. dose_range — Dose appropriateness for age, weight, indication
5. patient_profile — Age/gender/condition appropriateness, contraindications
6. prescriber_credentials — DEA authorization for controlled substances

Also provide:
- "overall_risk": "high" | "moderate" | "low" — aggregate risk level
- "reasoning": Multi-paragraph clinical analysis narrative explaining your assessment

Return ONLY valid JSON with this exact structure:
{
  "dur_review": {"status": "...", "findings": [...]},
  "drug_interactions": {"status": "...", "findings": [...]},
  "allergy_screening": {"status": "...", "findings": [...]},
  "dose_range": {"status": "...", "findings": [...]},
  "patient_profile": {"status": "...", "findings": [...]},
  "prescriber_credentials": {"status": "...", "findings": [...]},
  "overall_risk": "...",
  "reasoning": "..."
}"""

PRESCRIBE_SYSTEM_PROMPT = """You are a senior clinical pharmacist AI assistant helping determine appropriate prescribing details for a medication order. Given the patient profile, drug information, and clinical context, recommend prescribing parameters.

Consider:
- Patient demographics (age, gender, conditions, allergies)
- Drug characteristics (dosage form, strength, route, DEA schedule)
- Active medications (for interactions, duplicate therapy, therapeutic context)
- Standard prescribing guidelines for the drug class
- Whether this is a new therapy or continuation/renewal

Classify the prescription:
- "routine": Maintenance medication, regular ongoing schedule (30-90 day supply, multiple refills)
- "stat_supply": Short bridge fill to catch patient up to routine cycle (5-14 day supply, 0 refills)
- "acute": Time-limited therapy with defined course (antibiotics, steroids, etc.)
- "prn": As-needed medication with variable usage

Return ONLY valid JSON:
{
  "rx_classification": "routine" | "stat_supply" | "acute" | "prn",
  "classification_reasoning": "Why this classification was chosen",
  "quantity": <integer>,
  "days_supply": <integer>,
  "refills": <integer>,
  "sig_text": "Complete patient directions",
  "substitutions": 0,
  "reasoning": "Full prescribing reasoning narrative"
}"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _empty_findings(error: str | None = None) -> dict:
    """Return a valid empty CDS structure — used on error so frontend always renders."""
    result = {
        "dur_review": {"status": "clear", "findings": []},
        "drug_interactions": {"status": "clear", "findings": []},
        "allergy_screening": {"status": "clear", "findings": []},
        "dose_range": {"status": "clear", "findings": []},
        "patient_profile": {"status": "clear", "findings": []},
        "prescriber_credentials": {"status": "clear", "findings": []},
        "overall_risk": "low",
        "reasoning": "Clinical analysis could not be completed." if error else "",
        "_model": settings.ollama_model,
        "_generated_at": datetime.now(timezone.utc).isoformat(),
    }
    if error:
        result["_error"] = error
    return result


def _extract_thinking(text: str) -> tuple[str, str]:
    """Extract <think>...</think> blocks from qwen3 output. Returns (thinking, cleaned_text)."""
    pattern = re.compile(r"<think>(.*?)</think>", re.DOTALL)
    thinking_blocks = pattern.findall(text)
    cleaned = pattern.sub("", text).strip()
    return "\n\n".join(thinking_blocks).strip(), cleaned


def _calc_age(dob: str) -> int | None:
    """Calculate age from YYYY-MM-DD date of birth."""
    try:
        born = datetime.strptime(dob, "%Y-%m-%d")
        today = datetime.now()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ClinicalReviewService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit = AuditService(db)
        self.ollama_url = settings.ollama_url
        self.model = settings.ollama_model

    async def _load_rx(self, rx_id: str) -> Prescription:
        result = await self.db.execute(
            select(Prescription).where(Prescription.id == rx_id)
        )
        rx = result.scalar_one_or_none()
        if not rx:
            raise ValueError(f"Prescription {rx_id} not found")
        return rx

    async def _load_patient(self, patient_id: str | None) -> Patient | None:
        if not patient_id:
            return None
        result = await self.db.execute(
            select(Patient).where(Patient.id == patient_id)
        )
        return result.scalar_one_or_none()

    async def _load_active_meds(self, patient_id: str | None, exclude_rx_id: str) -> list[dict]:
        """Get all approved prescriptions for a patient (excluding current Rx)."""
        if not patient_id:
            return []
        result = await self.db.execute(
            select(Prescription).where(
                Prescription.patient_id == patient_id,
                Prescription.status == RxStatus.APPROVED,
                Prescription.id != exclude_rx_id,
            )
        )
        rxs = result.scalars().all()
        return [
            {
                "drug": r.drug_description,
                "ndc": r.ndc,
                "quantity": r.quantity,
                "days_supply": r.days_supply,
                "refills": r.refills,
                "sig": r.sig_text,
                "written_date": r.written_date,
            }
            for r in rxs
        ]

    async def _lookup_drug(self, ndc: str) -> dict | None:
        """Lookup drug details by NDC."""
        if not ndc:
            return None
        result = await self.db.execute(
            select(Drug).where(Drug.ndc == ndc)
        )
        drug = result.scalar_one_or_none()
        if not drug:
            return None
        return {
            "drug_name": drug.drug_name,
            "generic_name": drug.generic_name,
            "dosage_form": drug.dosage_form,
            "strength": drug.strength,
            "route": drug.route,
            "dea_schedule": drug.dea_schedule,
            "manufacturer": drug.manufacturer,
        }

    async def _call_ollama(self, system_prompt: str, user_prompt: str) -> tuple[str, str | None, int]:
        """Call Ollama and return (response_text, thinking, eval_duration_ms)."""
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": user_prompt,
                    "system": system_prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 4096,
                    },
                },
            )
            resp.raise_for_status()

        elapsed_ms = int((time.monotonic() - start) * 1000)
        body = resp.json()
        raw_text = body.get("response", "{}")

        # Extract qwen3 thinking blocks
        thinking, cleaned = _extract_thinking(raw_text)
        return cleaned, thinking or None, elapsed_ms

    # ------------------------------------------------------------------
    # Clinical Review (DUR + Patient Profile)
    # ------------------------------------------------------------------

    async def run_review(
        self,
        rx_id: str,
        *,
        actor_id: str = "pipeline-worker",
        actor_role: str = "agent",
        trigger: str = "pipeline",
    ) -> dict:
        """Run full clinical DUR + patient profile review for a prescription."""
        rx = await self._load_rx(rx_id)
        patient = await self._load_patient(rx.patient_id)
        active_meds = await self._load_active_meds(rx.patient_id, rx.id)
        drug_info = await self._lookup_drug(rx.ndc)

        # Build context prompt
        age = _calc_age(rx.patient_dob)
        lines = [
            "=== PRESCRIPTION UNDER REVIEW ===",
            f"Drug: {rx.drug_description}",
            f"NDC: {rx.ndc}",
            f"Quantity: {rx.quantity}  |  Days Supply: {rx.days_supply}  |  Refills: {rx.refills}",
            f"Sig: {rx.sig_text}",
            f"Written: {rx.written_date}  |  Substitutions: {rx.substitutions}",
            f"Prescriber: {rx.prescriber_name}  |  NPI: {rx.prescriber_npi}  |  DEA: {rx.prescriber_dea}",
        ]
        if drug_info:
            lines.append(f"\nDrug Details: {drug_info['generic_name']} | {drug_info['dosage_form']} | "
                         f"{drug_info['strength']} | {drug_info['route']} | "
                         f"Schedule: {drug_info['dea_schedule'] or 'None'}")

        lines.append(f"\n=== PATIENT ===")
        lines.append(f"Name: {rx.patient_first_name} {rx.patient_last_name}")
        lines.append(f"DOB: {rx.patient_dob}  |  Age: {age or 'Unknown'}")
        if patient:
            lines.append(f"Gender: {patient.gender}")
            allergies = patient.allergies or []
            if allergies:
                allergy_str = "; ".join(
                    f"{a.get('substance', '?')} ({a.get('reaction', '?')}, {a.get('severity', '?')})"
                    for a in allergies
                )
                lines.append(f"Allergies: {allergy_str}")
            else:
                lines.append("Allergies: NKDA (No Known Drug Allergies)")

            conditions = patient.conditions or []
            if conditions:
                lines.append(f"Conditions: {', '.join(conditions)}")
            else:
                lines.append("Conditions: None documented")

        if active_meds:
            lines.append(f"\n=== ACTIVE MEDICATIONS ({len(active_meds)}) ===")
            for i, med in enumerate(active_meds, 1):
                lines.append(f"{i}. {med['drug']} (NDC: {med['ndc']}) — "
                             f"Qty {med['quantity']} / {med['days_supply']}d / "
                             f"{med['refills']} refills — Sig: {med['sig']}")
        else:
            lines.append("\n=== ACTIVE MEDICATIONS ===\nNone on file")

        user_prompt = "\n".join(lines)

        # Call Ollama
        try:
            response_text, thinking, elapsed_ms = await self._call_ollama(
                CDS_SYSTEM_PROMPT, user_prompt
            )
            raw_findings = json.loads(response_text)

            # Merge with empty template so all 6 categories always exist
            template = _empty_findings()
            for cat in ("dur_review", "drug_interactions", "allergy_screening",
                        "dose_range", "patient_profile", "prescriber_credentials"):
                if cat in raw_findings and isinstance(raw_findings[cat], dict):
                    template[cat] = raw_findings[cat]
            # Copy top-level fields from LLM response
            if "overall_risk" in raw_findings:
                template["overall_risk"] = raw_findings["overall_risk"]
            if "reasoning" in raw_findings:
                template["reasoning"] = raw_findings["reasoning"]
            findings = template

            # Enrich with metadata
            findings["_thinking"] = thinking
            findings["_model"] = self.model
            findings["_generated_at"] = datetime.now(timezone.utc).isoformat()
            findings["_eval_duration_ms"] = elapsed_ms
            findings["_trigger"] = trigger

        except httpx.TimeoutException:
            logger.error("Ollama timeout for rx %s (120s exceeded)", rx_id[:8])
            findings = _empty_findings("Ollama timeout — analysis took too long")
        except httpx.ConnectError:
            logger.error("Ollama connection failed for rx %s", rx_id[:8])
            findings = _empty_findings("Ollama unavailable — service not running")
        except (json.JSONDecodeError, KeyError) as exc:
            logger.error("Bad JSON from Ollama for rx %s: %s", rx_id[:8], exc)
            findings = _empty_findings(f"Invalid AI response format: {exc}")
        except Exception as exc:
            logger.exception("Clinical review failed for rx %s", rx_id[:8])
            findings = _empty_findings(str(exc))

        # Store findings on Rx
        rx.clinical_findings = findings
        await self.db.flush()

        # Audit log
        flagged = [
            cat for cat in ["dur_review", "drug_interactions", "allergy_screening",
                            "dose_range", "patient_profile", "prescriber_credentials"]
            if findings.get(cat, {}).get("status") == "flagged"
        ]
        await self.audit.log(
            action="prescription.clinical_review",
            actor_id=actor_id,
            actor_role=actor_role,
            resource_type="prescription",
            resource_id=rx_id,
            detail={
                "overall_risk": findings.get("overall_risk"),
                "flagged_categories": flagged,
                "model": findings.get("_model"),
                "eval_duration_ms": findings.get("_eval_duration_ms"),
                "trigger": trigger,
                "error": findings.get("_error"),
            },
        )
        await self.db.commit()

        logger.info(
            "Clinical review for rx %s: risk=%s flagged=%s (%dms)",
            rx_id[:8],
            findings.get("overall_risk", "?"),
            flagged or "none",
            findings.get("_eval_duration_ms", 0),
        )
        return findings

    # ------------------------------------------------------------------
    # Prescribe Assist (AI-powered Rx generation)
    # ------------------------------------------------------------------

    async def prescribe_assist(
        self,
        *,
        patient_id: str,
        drug_id: str,
        prescriber_npi: str,
        actor_id: str,
        actor_role: str,
    ) -> dict:
        """AI-assisted prescribing — given patient + drug, generate Rx details."""
        # Load patient
        patient = await self._load_patient(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        # Load drug by ID
        result = await self.db.execute(select(Drug).where(Drug.id == drug_id))
        drug = result.scalar_one_or_none()
        if not drug:
            raise ValueError(f"Drug {drug_id} not found")

        # Load active meds
        active_meds = await self._load_active_meds(patient_id, exclude_rx_id="")
        age = _calc_age(patient.date_of_birth)

        # Check for existing Rx of same drug class
        same_drug_history = [
            m for m in active_meds
            if drug.generic_name.lower().split()[0] in m["drug"].lower()
        ]

        # Build prompt
        lines = [
            "=== DRUG TO PRESCRIBE ===",
            f"Drug: {drug.drug_name}",
            f"Generic: {drug.generic_name}",
            f"Form: {drug.dosage_form}  |  Strength: {drug.strength}  |  Route: {drug.route}",
            f"DEA Schedule: {drug.dea_schedule or 'Non-controlled'}",
            f"\n=== PATIENT ===",
            f"Name: {patient.first_name} {patient.last_name}",
            f"DOB: {patient.date_of_birth}  |  Age: {age or 'Unknown'}  |  Gender: {patient.gender}",
        ]

        allergies = patient.allergies or []
        if allergies:
            allergy_str = "; ".join(
                f"{a.get('substance', '?')} ({a.get('reaction', '?')}, {a.get('severity', '?')})"
                for a in allergies
            )
            lines.append(f"Allergies: {allergy_str}")
        else:
            lines.append("Allergies: NKDA")

        conditions = patient.conditions or []
        if conditions:
            lines.append(f"Conditions: {', '.join(conditions)}")

        if active_meds:
            lines.append(f"\n=== ACTIVE MEDICATIONS ({len(active_meds)}) ===")
            for i, med in enumerate(active_meds, 1):
                lines.append(f"{i}. {med['drug']} — Qty {med['quantity']} / "
                             f"{med['days_supply']}d / {med['refills']} refills — "
                             f"Written: {med['written_date']}")
        else:
            lines.append("\n=== ACTIVE MEDICATIONS ===\nNone on file")

        if same_drug_history:
            lines.append(f"\n=== SAME DRUG HISTORY ===")
            lines.append("Patient has active Rx for this drug or drug class:")
            for m in same_drug_history:
                lines.append(f"  - {m['drug']} — Written: {m['written_date']} — "
                             f"Qty {m['quantity']} / {m['days_supply']}d")

        lines.append(f"\nPrescriber NPI: {prescriber_npi}")

        user_prompt = "\n".join(lines)

        try:
            response_text, thinking, elapsed_ms = await self._call_ollama(
                PRESCRIBE_SYSTEM_PROMPT, user_prompt
            )
            result_data = json.loads(response_text)

            # Apply hard rules
            if drug.dea_schedule in ("CII",):
                result_data["refills"] = 0  # CII cannot have refills

            # Enrich
            result_data["drug_description"] = drug.drug_name
            result_data["ndc"] = drug.ndc
            result_data["_thinking"] = thinking
            result_data["_model"] = self.model
            result_data["_generated_at"] = datetime.now(timezone.utc).isoformat()
            result_data["_eval_duration_ms"] = elapsed_ms

        except httpx.TimeoutException:
            raise ValueError("AI prescribing timed out — please try again")
        except httpx.ConnectError:
            raise ValueError("AI service unavailable — Ollama not running")
        except (json.JSONDecodeError, KeyError) as exc:
            raise ValueError(f"Invalid AI response: {exc}")

        # Audit
        await self.audit.log(
            action="prescription.prescribe_assist",
            actor_id=actor_id,
            actor_role=actor_role,
            resource_type="drug",
            resource_id=drug_id,
            detail={
                "patient_id": patient_id,
                "drug_name": drug.drug_name,
                "ndc": drug.ndc,
                "classification": result_data.get("rx_classification"),
                "model": self.model,
                "eval_duration_ms": elapsed_ms,
            },
        )
        await self.db.commit()

        return result_data

    # ------------------------------------------------------------------
    # SSE Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sse_event(event_type: str, data: dict) -> str:
        """Format a single SSE event."""
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    async def _call_ollama_stream(
        self, system_prompt: str, user_prompt: str
    ) -> AsyncGenerator[tuple[str, bool, str | None], None]:
        """Stream Ollama response token-by-token. Yields (token, is_done, full_text_if_done)."""
        full_text = ""
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream(
                "POST",
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": user_prompt,
                    "system": system_prompt,
                    "stream": True,
                    "format": "json",
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 4096,
                    },
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    done = chunk.get("done", False)
                    full_text += token
                    if done:
                        yield token, True, full_text
                    else:
                        yield token, False, None

    def _build_review_prompt(
        self,
        rx: Prescription,
        patient: Patient | None,
        active_meds: list[dict],
        drug_info: dict | None,
    ) -> str:
        """Build the user prompt for clinical review."""
        age = _calc_age(rx.patient_dob)
        lines = [
            "=== PRESCRIPTION UNDER REVIEW ===",
            f"Drug: {rx.drug_description}",
            f"NDC: {rx.ndc}",
            f"Quantity: {rx.quantity}  |  Days Supply: {rx.days_supply}  |  Refills: {rx.refills}",
            f"Sig: {rx.sig_text}",
            f"Written: {rx.written_date}  |  Substitutions: {rx.substitutions}",
            f"Prescriber: {rx.prescriber_name}  |  NPI: {rx.prescriber_npi}  |  DEA: {rx.prescriber_dea}",
        ]
        if drug_info:
            lines.append(f"\nDrug Details: {drug_info['generic_name']} | {drug_info['dosage_form']} | "
                         f"{drug_info['strength']} | {drug_info['route']} | "
                         f"Schedule: {drug_info['dea_schedule'] or 'None'}")
        lines.append("\n=== PATIENT ===")
        lines.append(f"Name: {rx.patient_first_name} {rx.patient_last_name}")
        lines.append(f"DOB: {rx.patient_dob}  |  Age: {age or 'Unknown'}")
        if patient:
            lines.append(f"Gender: {patient.gender}")
            allergies = patient.allergies or []
            if allergies:
                allergy_str = "; ".join(
                    f"{a.get('substance', '?')} ({a.get('reaction', '?')}, {a.get('severity', '?')})"
                    for a in allergies
                )
                lines.append(f"Allergies: {allergy_str}")
            else:
                lines.append("Allergies: NKDA (No Known Drug Allergies)")
            conditions = patient.conditions or []
            if conditions:
                lines.append(f"Conditions: {', '.join(conditions)}")
            else:
                lines.append("Conditions: None documented")
        if active_meds:
            lines.append(f"\n=== ACTIVE MEDICATIONS ({len(active_meds)}) ===")
            for i, med in enumerate(active_meds, 1):
                lines.append(f"{i}. {med['drug']} (NDC: {med['ndc']}) — "
                             f"Qty {med['quantity']} / {med['days_supply']}d / "
                             f"{med['refills']} refills — Sig: {med['sig']}")
        else:
            lines.append("\n=== ACTIVE MEDICATIONS ===\nNone on file")
        return "\n".join(lines)

    def _build_prescribe_prompt(
        self,
        patient: Patient,
        drug: Drug,
        active_meds: list[dict],
        same_drug_history: list[dict],
        prescriber_npi: str,
    ) -> str:
        """Build the user prompt for prescribe-assist."""
        age = _calc_age(patient.date_of_birth)
        lines = [
            "=== DRUG TO PRESCRIBE ===",
            f"Drug: {drug.drug_name}",
            f"Generic: {drug.generic_name}",
            f"Form: {drug.dosage_form}  |  Strength: {drug.strength}  |  Route: {drug.route}",
            f"DEA Schedule: {drug.dea_schedule or 'Non-controlled'}",
            "\n=== PATIENT ===",
            f"Name: {patient.first_name} {patient.last_name}",
            f"DOB: {patient.date_of_birth}  |  Age: {age or 'Unknown'}  |  Gender: {patient.gender}",
        ]
        allergies = patient.allergies or []
        if allergies:
            allergy_str = "; ".join(
                f"{a.get('substance', '?')} ({a.get('reaction', '?')}, {a.get('severity', '?')})"
                for a in allergies
            )
            lines.append(f"Allergies: {allergy_str}")
        else:
            lines.append("Allergies: NKDA")
        conditions = patient.conditions or []
        if conditions:
            lines.append(f"Conditions: {', '.join(conditions)}")
        if active_meds:
            lines.append(f"\n=== ACTIVE MEDICATIONS ({len(active_meds)}) ===")
            for i, med in enumerate(active_meds, 1):
                lines.append(f"{i}. {med['drug']} — Qty {med['quantity']} / "
                             f"{med['days_supply']}d / {med['refills']} refills — "
                             f"Written: {med['written_date']}")
        else:
            lines.append("\n=== ACTIVE MEDICATIONS ===\nNone on file")
        if same_drug_history:
            lines.append("\n=== SAME DRUG HISTORY ===")
            lines.append("Patient has active Rx for this drug or drug class:")
            for m in same_drug_history:
                lines.append(f"  - {m['drug']} — Written: {m['written_date']} — "
                             f"Qty {m['quantity']} / {m['days_supply']}d")
        lines.append(f"\nPrescriber NPI: {prescriber_npi}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # SSE Streaming: Clinical Review
    # ------------------------------------------------------------------

    async def run_review_stream(
        self,
        rx_id: str,
        *,
        actor_id: str,
        actor_role: str,
    ) -> AsyncGenerator[str, None]:
        """Stream clinical review as SSE events through 4 pipeline stages."""
        # Stage 1: Data Gathering
        yield self._sse_event("stage", {"stage": "data_gathering", "status": "started"})
        t0 = time.monotonic()
        try:
            rx = await self._load_rx(rx_id)
            patient = await self._load_patient(rx.patient_id)
            active_meds = await self._load_active_meds(rx.patient_id, rx.id)
            drug_info = await self._lookup_drug(rx.ndc)
        except Exception as exc:
            yield self._sse_event("error", {"message": str(exc)})
            return
        data_ms = int((time.monotonic() - t0) * 1000)
        context = {
            "patient": f"{rx.patient_first_name} {rx.patient_last_name}",
            "drug": rx.drug_description,
            "active_meds_count": len(active_meds),
            "has_allergies": bool(patient and patient.allergies),
            "has_conditions": bool(patient and patient.conditions),
        }
        yield self._sse_event("stage", {
            "stage": "data_gathering", "status": "complete",
            "timing_ms": data_ms, "context": context,
        })

        # Stage 2: Prompt Construction
        yield self._sse_event("stage", {"stage": "prompt_construction", "status": "started"})
        t1 = time.monotonic()
        user_prompt = self._build_review_prompt(rx, patient, active_meds, drug_info)
        prompt_ms = int((time.monotonic() - t1) * 1000)
        yield self._sse_event("stage", {
            "stage": "prompt_construction", "status": "complete",
            "timing_ms": prompt_ms,
            "prompt_preview": user_prompt[:500],
            "prompt_length": len(user_prompt),
        })

        # Stage 3: LLM Inference (streaming)
        yield self._sse_event("stage", {
            "stage": "llm_inference", "status": "started", "model": self.model,
        })
        t2 = time.monotonic()
        full_text = ""
        try:
            async for token, is_done, done_text in self._call_ollama_stream(
                CDS_SYSTEM_PROMPT, user_prompt
            ):
                if token:
                    yield self._sse_event("token", {"text": token})
                if is_done and done_text is not None:
                    full_text = done_text
        except httpx.ConnectError:
            yield self._sse_event("error", {"message": "Ollama unavailable — service not running"})
            return
        except httpx.TimeoutException:
            yield self._sse_event("error", {"message": "Ollama timeout — analysis took too long"})
            return
        except Exception as exc:
            yield self._sse_event("error", {"message": str(exc)})
            return
        llm_ms = int((time.monotonic() - t2) * 1000)
        yield self._sse_event("stage", {
            "stage": "llm_inference", "status": "complete", "timing_ms": llm_ms,
        })

        # Stage 4: Response Parsing
        yield self._sse_event("stage", {"stage": "response_parsing", "status": "started"})
        t3 = time.monotonic()
        try:
            thinking, cleaned = _extract_thinking(full_text)
            raw_findings = json.loads(cleaned)
            template = _empty_findings()
            for cat in ("dur_review", "drug_interactions", "allergy_screening",
                        "dose_range", "patient_profile", "prescriber_credentials"):
                if cat in raw_findings and isinstance(raw_findings[cat], dict):
                    template[cat] = raw_findings[cat]
            if "overall_risk" in raw_findings:
                template["overall_risk"] = raw_findings["overall_risk"]
            if "reasoning" in raw_findings:
                template["reasoning"] = raw_findings["reasoning"]
            findings = template
            findings["_thinking"] = thinking or None
            findings["_model"] = self.model
            findings["_generated_at"] = datetime.now(timezone.utc).isoformat()
            findings["_eval_duration_ms"] = llm_ms
            findings["_trigger"] = "manual-stream"
        except (json.JSONDecodeError, KeyError) as exc:
            logger.error("Bad JSON from Ollama stream for rx %s: %s", rx_id[:8], exc)
            findings = _empty_findings(f"Invalid AI response format: {exc}")

        parse_ms = int((time.monotonic() - t3) * 1000)
        yield self._sse_event("stage", {
            "stage": "response_parsing", "status": "complete", "timing_ms": parse_ms,
        })

        # Store findings + audit
        rx.clinical_findings = findings
        await self.db.flush()
        flagged = [
            cat for cat in ["dur_review", "drug_interactions", "allergy_screening",
                            "dose_range", "patient_profile", "prescriber_credentials"]
            if findings.get(cat, {}).get("status") == "flagged"
        ]
        await self.audit.log(
            action="prescription.clinical_review",
            actor_id=actor_id,
            actor_role=actor_role,
            resource_type="prescription",
            resource_id=rx_id,
            detail={
                "overall_risk": findings.get("overall_risk"),
                "flagged_categories": flagged,
                "model": self.model,
                "eval_duration_ms": llm_ms,
                "trigger": "manual-stream",
            },
        )
        await self.db.commit()

        yield self._sse_event("complete", findings)

    # ------------------------------------------------------------------
    # SSE Streaming: Prescribe Assist
    # ------------------------------------------------------------------

    async def prescribe_assist_stream(
        self,
        *,
        patient_id: str,
        drug_id: str,
        prescriber_npi: str,
        actor_id: str,
        actor_role: str,
    ) -> AsyncGenerator[str, None]:
        """Stream prescribe-assist as SSE events through 4 pipeline stages."""
        # Stage 1: Data Gathering
        yield self._sse_event("stage", {"stage": "data_gathering", "status": "started"})
        t0 = time.monotonic()
        try:
            patient = await self._load_patient(patient_id)
            if not patient:
                yield self._sse_event("error", {"message": f"Patient {patient_id} not found"})
                return
            result = await self.db.execute(select(Drug).where(Drug.id == drug_id))
            drug = result.scalar_one_or_none()
            if not drug:
                yield self._sse_event("error", {"message": f"Drug {drug_id} not found"})
                return
            active_meds = await self._load_active_meds(patient_id, exclude_rx_id="")
            same_drug_history = [
                m for m in active_meds
                if drug.generic_name.lower().split()[0] in m["drug"].lower()
            ]
        except Exception as exc:
            yield self._sse_event("error", {"message": str(exc)})
            return
        data_ms = int((time.monotonic() - t0) * 1000)
        context = {
            "patient": f"{patient.first_name} {patient.last_name}",
            "drug": drug.drug_name,
            "active_meds_count": len(active_meds),
            "same_drug_history_count": len(same_drug_history),
        }
        yield self._sse_event("stage", {
            "stage": "data_gathering", "status": "complete",
            "timing_ms": data_ms, "context": context,
        })

        # Stage 2: Prompt Construction
        yield self._sse_event("stage", {"stage": "prompt_construction", "status": "started"})
        t1 = time.monotonic()
        user_prompt = self._build_prescribe_prompt(
            patient, drug, active_meds, same_drug_history, prescriber_npi
        )
        prompt_ms = int((time.monotonic() - t1) * 1000)
        yield self._sse_event("stage", {
            "stage": "prompt_construction", "status": "complete",
            "timing_ms": prompt_ms,
            "prompt_preview": user_prompt[:500],
            "prompt_length": len(user_prompt),
        })

        # Stage 3: LLM Inference (streaming)
        yield self._sse_event("stage", {
            "stage": "llm_inference", "status": "started", "model": self.model,
        })
        t2 = time.monotonic()
        full_text = ""
        try:
            async for token, is_done, done_text in self._call_ollama_stream(
                PRESCRIBE_SYSTEM_PROMPT, user_prompt
            ):
                if token:
                    yield self._sse_event("token", {"text": token})
                if is_done and done_text is not None:
                    full_text = done_text
        except httpx.ConnectError:
            yield self._sse_event("error", {"message": "Ollama unavailable — service not running"})
            return
        except httpx.TimeoutException:
            yield self._sse_event("error", {"message": "Ollama timeout"})
            return
        except Exception as exc:
            yield self._sse_event("error", {"message": str(exc)})
            return
        llm_ms = int((time.monotonic() - t2) * 1000)
        yield self._sse_event("stage", {
            "stage": "llm_inference", "status": "complete", "timing_ms": llm_ms,
        })

        # Stage 4: Response Parsing
        yield self._sse_event("stage", {"stage": "response_parsing", "status": "started"})
        t3 = time.monotonic()
        try:
            thinking, cleaned = _extract_thinking(full_text)
            result_data = json.loads(cleaned)
            if drug.dea_schedule in ("CII",):
                result_data["refills"] = 0
            result_data["drug_description"] = drug.drug_name
            result_data["ndc"] = drug.ndc
            result_data["_thinking"] = thinking or None
            result_data["_model"] = self.model
            result_data["_generated_at"] = datetime.now(timezone.utc).isoformat()
            result_data["_eval_duration_ms"] = llm_ms
        except (json.JSONDecodeError, KeyError) as exc:
            yield self._sse_event("error", {"message": f"Invalid AI response: {exc}"})
            return
        parse_ms = int((time.monotonic() - t3) * 1000)
        yield self._sse_event("stage", {
            "stage": "response_parsing", "status": "complete", "timing_ms": parse_ms,
        })

        # Audit
        await self.audit.log(
            action="prescription.prescribe_assist",
            actor_id=actor_id,
            actor_role=actor_role,
            resource_type="drug",
            resource_id=drug_id,
            detail={
                "patient_id": patient_id,
                "drug_name": drug.drug_name,
                "ndc": drug.ndc,
                "classification": result_data.get("rx_classification"),
                "model": self.model,
                "eval_duration_ms": llm_ms,
            },
        )
        await self.db.commit()

        yield self._sse_event("complete", result_data)
