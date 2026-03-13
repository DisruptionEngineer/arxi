"""3-tier patient matching: exact -> LLM-assisted -> auto-create."""

import json
import logging
from dataclasses import dataclass
from typing import Literal

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from arxi.config import settings
from arxi.events import Event, event_bus
from arxi.modules.intake.models import Prescription
from arxi.modules.patient.models import Patient
from arxi.modules.patient.normalization import normalize_name
from arxi.modules.patient.service import PatientService

logger = logging.getLogger("arxi.patient.matcher")

OLLAMA_TIMEOUT = 5.0

LLM_PROMPT_TEMPLATE = """You are a patient matching assistant for a pharmacy system.

Given the incoming prescription patient data and a list of existing patient candidates, determine if any candidate is the same person.

Incoming patient:
- Name: {first_name} {last_name}
- Date of Birth: {dob}

Candidates:
{candidate_list}

Respond with JSON only:
- If a candidate matches: {{"match": "<patient_id>", "confidence": "high|medium", "reason": "..."}}
- If no candidate matches: {{"match": null, "reason": "..."}}"""


@dataclass
class MatchResult:
    outcome: Literal["linked", "created", "failed"]
    patient_id: str | None
    tier: int
    confidence: str
    detail: str


class PatientMatcher:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.patient_svc = PatientService(db)

    async def match_and_link(self, rx: Prescription) -> MatchResult:
        norm_first = normalize_name(rx.patient_first_name)
        norm_last = normalize_name(rx.patient_last_name)
        dob = rx.patient_dob

        # --- Tier 1: Exact match ---
        candidates = await self.patient_svc.search(
            last_name=norm_last, first_name=norm_first, dob=dob
        )

        if len(candidates) == 1:
            rx.patient_id = candidates[0].id
            await self.db.commit()
            await event_bus.publish(Event(
                type="patient.linked",
                resource_id=rx.id,
                data={
                    "patient_id": candidates[0].id,
                    "patient_name": f"{candidates[0].first_name} {candidates[0].last_name}",
                    "match_tier": 1,
                },
                actor_id="patient-matcher",
            ))
            return MatchResult(
                outcome="linked",
                patient_id=candidates[0].id,
                tier=1,
                confidence="high",
                detail=f"Exact match: {candidates[0].first_name} {candidates[0].last_name}",
            )

        # --- Tier 2: LLM judgment ---
        if len(candidates) == 0:
            prefix = norm_last[:3] if len(norm_last) >= 3 else norm_last
            candidates = await self.patient_svc.search_fuzzy(
                dob=dob, last_name_prefix=prefix
            )

        if candidates:
            llm_result = await self._tier2_llm_match(rx, candidates)
            if llm_result:
                rx.patient_id = llm_result
                await self.db.commit()
                await event_bus.publish(Event(
                    type="patient.linked",
                    resource_id=rx.id,
                    data={
                        "patient_id": llm_result,
                        "patient_name": f"{rx.patient_first_name} {rx.patient_last_name}",
                        "match_tier": 2,
                    },
                    actor_id="patient-matcher",
                ))
                return MatchResult(
                    outcome="linked",
                    patient_id=llm_result,
                    tier=2,
                    confidence="medium",
                    detail="LLM-assisted match",
                )

        # --- Tier 3: Auto-create ---
        return await self._tier3_create(rx)

    async def _tier2_llm_match(
        self, rx: Prescription, candidates: list[Patient]
    ) -> str | None:
        candidate_list = "\n".join(
            f"- ID: {c.id}, Name: {c.first_name} {c.last_name}, "
            f"DOB: {c.date_of_birth}, Address: {c.address_line1} {c.city} {c.state}"
            for c in candidates
        )

        prompt = LLM_PROMPT_TEMPLATE.format(
            first_name=rx.patient_first_name,
            last_name=rx.patient_last_name,
            dob=rx.patient_dob,
            candidate_list=candidate_list,
        )

        try:
            async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
                resp = await client.post(
                    f"{settings.ollama_url}/api/generate",
                    json={
                        "model": settings.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                    },
                )

            if resp.status_code != 200:
                logger.warning("Ollama returned status %d", resp.status_code)
                return None

            body = resp.json()
            response_text = body.get("response", "")
            parsed = json.loads(response_text)
            match_id = parsed.get("match")

            if match_id:
                valid_ids = {c.id for c in candidates}
                if match_id in valid_ids:
                    return match_id
                logger.warning("LLM returned invalid patient ID: %s", match_id)

            return None

        except httpx.TimeoutException:
            logger.warning("Ollama timeout after %.1fs", OLLAMA_TIMEOUT)
            return None
        except (json.JSONDecodeError, KeyError, TypeError):
            logger.warning("Malformed LLM response", exc_info=True)
            return None
        except Exception:
            logger.warning("Tier 2 LLM match failed", exc_info=True)
            return None

    async def _tier3_create(self, rx: Prescription) -> MatchResult:
        patient = await self.patient_svc.create({
            "first_name": rx.patient_first_name,
            "last_name": rx.patient_last_name,
            "gender": "",
            "date_of_birth": rx.patient_dob,
        })
        rx.patient_id = patient.id
        await self.db.commit()
        await event_bus.publish(Event(
            type="patient.created",
            resource_id=rx.id,
            data={
                "patient_id": patient.id,
                "patient_name": f"{patient.first_name} {patient.last_name}",
            },
            actor_id="patient-matcher",
        ))
        return MatchResult(
            outcome="created",
            patient_id=patient.id,
            tier=3,
            confidence="low",
            detail=f"Auto-created patient: {patient.first_name} {patient.last_name}",
        )
