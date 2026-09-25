from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import get_current_actor
from app.models.audit_event import AuditEvent
from app.models.enums import AuditEventType


async def create_audit_event(
    session: AsyncSession,
    *,
    event_type: AuditEventType | str,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    study_id: UUID | None = None,
    actor: str | None = None,
    payload: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        event_type=str(event_type),
        entity_type=entity_type,
        entity_id=entity_id,
        study_id=study_id,
        actor=(
            actor
            if actor is not None
            else get_current_actor()
        ),
        payload=payload or {},
    )

    session.add(event)

    await session.flush()

    return event
