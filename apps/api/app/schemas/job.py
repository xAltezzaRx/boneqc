from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import AnalysisJobStatus


class AnalysisJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    study_id: UUID
    qc_analysis_id: UUID | None
    status: AnalysisJobStatus
    attempts: int
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime
