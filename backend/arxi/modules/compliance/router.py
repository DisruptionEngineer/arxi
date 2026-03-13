from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from arxi.auth.middleware import get_current_user
from arxi.auth.models import Role, User
from arxi.database import get_db
from arxi.modules.compliance.schemas import AuditLogEntry, AuditLogResponse
from arxi.modules.compliance.service import AuditService

router = APIRouter(prefix="/api/audit", tags=["audit"])


def _require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/logs", response_model=AuditLogResponse)
async def list_audit_logs(
    action: str | None = Query(None),
    actor_id: str | None = Query(None),
    resource_id: str | None = Query(None),
    resource_type: str | None = Query(None),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _admin: User = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    svc = AuditService(db)
    logs, total = await svc.query_filtered(
        action=action,
        actor_id=actor_id,
        resource_id=resource_id,
        resource_type=resource_type,
        from_date=from_date,
        to_date=to_date,
        search=search,
        limit=limit,
        offset=offset,
    )
    return AuditLogResponse(
        logs=[AuditLogEntry.model_validate(log) for log in logs],
        total=total,
    )
