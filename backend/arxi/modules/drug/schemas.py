from pydantic import BaseModel


class DrugResponse(BaseModel):
    id: str
    ndc: str
    drug_name: str
    generic_name: str
    dosage_form: str
    strength: str
    route: str
    manufacturer: str
    dea_schedule: str
    package_description: str

    model_config = {"from_attributes": True}


class DrugSearchResponse(BaseModel):
    drugs: list[DrugResponse]
    total: int
