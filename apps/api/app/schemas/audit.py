from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID

    event_type: str

    entity_type: str | None
    entity_id: UUID | None

    study_id: UUID | None

    actor: str | None

    payload: dict[str, Any]

    created_at: datetime
    updated_at: datetime


class AuditTimelineResponse(BaseModel):
    study_id: UUID
    events: list[AuditEventResponse]
