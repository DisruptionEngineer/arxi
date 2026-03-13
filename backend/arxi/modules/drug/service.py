from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from arxi.modules.drug.models import Drug


class DrugService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(self, query: str, *, limit: int = 15) -> list[Drug]:
        """Search drugs by name or NDC prefix. Used for autocomplete."""
        q = query.strip()
        if not q:
            return []

        # NDC search (starts with digits or dash pattern)
        is_ndc = q.replace("-", "").replace(" ", "").isdigit()

        if is_ndc:
            normalized = q.replace("-", "").replace(" ", "")
            stmt = (
                select(Drug)
                .where(func.replace(Drug.ndc, "-", "").startswith(normalized))
                .order_by(Drug.drug_name)
                .limit(limit)
            )
        else:
            pattern = f"%{q.lower()}%"
            stmt = (
                select(Drug)
                .where(
                    or_(
                        func.lower(Drug.drug_name).like(pattern),
                        func.lower(Drug.generic_name).like(pattern),
                    )
                )
                .order_by(Drug.drug_name)
                .limit(limit)
            )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_ndc(self, ndc: str) -> Drug | None:
        result = await self.db.execute(
            select(Drug).where(Drug.ndc == ndc)
        )
        return result.scalar_one_or_none()

    async def get(self, drug_id: str) -> Drug | None:
        result = await self.db.execute(
            select(Drug).where(Drug.id == drug_id)
        )
        return result.scalar_one_or_none()
