import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import AuditLog


async def log_action(
    db: AsyncSession,
    action: str,
    entity_type: str = None,
    entity_id: str = None,
    actor: str = "anonymous",
    ip_address: str = None,
    session_id: str = None,
    details: dict = None,
) -> AuditLog:
    entry = AuditLog(
        id=uuid.uuid4(),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        actor=actor,
        ip_address=ip_address,
        session_id=session_id,
        details=details,
        created_at=datetime.utcnow(),
    )
    db.add(entry)
    await db.flush()
    return entry
