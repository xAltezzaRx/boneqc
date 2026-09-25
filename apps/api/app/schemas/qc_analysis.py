from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import QCAnalysisStatus


class QCAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    study_id: UUID
    status: QCAnalysisStatus
    decision: str | None
    quality_score: float | None
    created_at: datetime
    updated_at: datetime
