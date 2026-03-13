from datetime import datetime

from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from arxi.modules.compliance.models import AuditLog


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        *,
        action: str,
        actor_id: str,
        actor_role: str,
        resource_type: str,
        resource_id: str,
        detail: dict | None = None,
        before_state: dict | None = None,
        after_state: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            action=action,
            actor_id=actor_id,
            actor_role=actor_role,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail,
            before_state=before_state,
            after_state=after_state,
        )
        self.db.add(entry)
        await self.db.flush()  # flush, don't commit — let caller manage transaction
        return entry

    async def query(
        self,
        *,
        resource_id: str | None = None,
        actor_id: str | None = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        stmt = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
        if resource_id is not None:
            stmt = stmt.where(AuditLog.resource_id == resource_id)
        if actor_id is not None:
            stmt = stmt.where(AuditLog.actor_id == actor_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def query_filtered(
        self,
        *,
        action: str | None = None,
        actor_id: str | None = None,
        resource_id: str | None = None,
        resource_type: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        """Query audit logs with filters, pagination, and total count."""
        base = select(AuditLog)

        if action is not None:
            base = base.where(AuditLog.action == action)
        if actor_id is not None:
            base = base.where(AuditLog.actor_id == actor_id)
        if resource_id is not None:
            base = base.where(AuditLog.resource_id == resource_id)
        if resource_type is not None:
            base = base.where(AuditLog.resource_type == resource_type)
        if from_date is not None:
            base = base.where(AuditLog.timestamp >= from_date)
        if to_date is not None:
            base = base.where(AuditLog.timestamp <= to_date)
        if search is not None:
            escaped = search.replace("%", r"\%").replace("_", r"\_")
            base = base.where(cast(AuditLog.detail, String).ilike(f"%{escaped}%"))

        # Total count (before pagination)
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        # Paginated results
        data_stmt = base.order_by(AuditLog.timestamp.desc(), AuditLog.id).limit(limit).offset(offset)
        result = await self.db.execute(data_stmt)
        return list(result.scalars().all()), total
