import httpx


class IntakeAgent:
    def __init__(self, *, ollama_url: str, model: str):
        self.ollama_url = ollama_url
        self.model = model

    def validate_rx_fields(self, rx_data: dict) -> dict:
        """Rule-based validation (no LLM needed). Fast, deterministic."""
        issues = []
        required = [
            "patient_first_name",
            "patient_last_name",
            "drug_description",
            "ndc",
            "quantity",
            "sig_text",
        ]
        for field in required:
            val = rx_data.get(field)
            if not val or (isinstance(val, str) and not val.strip()):
                issues.append(f"Missing required field: {field}")

        ndc = rx_data.get("ndc", "")
        if ndc and len(ndc.replace("-", "")) != 11:
            issues.append(f"NDC code '{ndc}' is not 11 digits")

        qty = rx_data.get("quantity", 0)
        if isinstance(qty, int) and qty <= 0:
            issues.append("Quantity must be greater than 0")

        refills = rx_data.get("refills", 0)
        if isinstance(refills, int) and refills > 11:
            issues.append(f"Refill count {refills} exceeds maximum (11)")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "confidence": 1.0 if not issues else 0.5,
        }

    async def llm_review(self, rx_data: dict, system_prompt: str) -> dict:
        """Use Ollama for deeper review (ambiguity detection, sig interpretation)."""
        import json as json_mod

        prompt = (
            f"Review this prescription data:\n{rx_data}\n\n"
            "Return JSON: {valid, issues, confidence}"
        )
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "format": "json",
                },
            )
            resp.raise_for_status()
            response_text = resp.json().get("response", "{}")
            return json_mod.loads(response_text)
