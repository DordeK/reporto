from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from app.database import get_db
from app.models.models import AuditLog

router = APIRouter()


@router.get("/")
async def list_audit_logs(
    action: str = Query(None),
    entity_type: str = Query(None),
    actor: str = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(AuditLog).order_by(AuditLog.created_at.desc())
    if action:
        q = q.where(AuditLog.action == action)
    if entity_type:
        q = q.where(AuditLog.entity_type == entity_type)
    if actor:
        q = q.where(AuditLog.actor == actor)

    count_q = select(func.count()).select_from(q.subquery())
    total_result = await db.execute(count_q)
    total = total_result.scalar()

    q = q.offset((page - 1) * limit).limit(limit)
    result = await db.execute(q)
    logs = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": [
            {
                "id": str(log.id),
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "actor": log.actor,
                "ip_address": log.ip_address,
                "session_id": log.session_id,
                "details": log.details,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ]
    }
