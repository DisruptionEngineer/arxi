from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from arxi.auth.middleware import get_current_user
from arxi.auth.models import User
from arxi.database import get_db
from arxi.modules.drug.schemas import DrugResponse, DrugSearchResponse
from arxi.modules.drug.service import DrugService

router = APIRouter(prefix="/api/drugs", tags=["drugs"])


@router.get("/search", response_model=DrugSearchResponse)
async def search_drugs(
    q: str = Query(..., min_length=2, description="Drug name or NDC prefix"),
    limit: int = Query(15, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Typeahead drug search by name or NDC."""
    svc = DrugService(db)
    drugs = await svc.search(q, limit=limit)
    return DrugSearchResponse(drugs=drugs, total=len(drugs))


@router.get("/ndc/{ndc}", response_model=DrugResponse)
async def get_drug_by_ndc(
    ndc: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Look up a drug by NDC code."""
    svc = DrugService(db)
    drug = await svc.get_by_ndc(ndc)
    if not drug:
        raise HTTPException(status_code=404, detail="Drug not found")
    return drug
