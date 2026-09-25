from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import AnalysisResultStatus

from app.schemas.audit import AuditEventResponse
from app.schemas.job import AnalysisJobResponse
from app.schemas.qc_analysis import QCAnalysisResponse
from app.schemas.model_version import ModelVersionResponse
from app.schemas.study import StudyDetailResponse


class AnalysisResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    study_id: UUID
    job_id: UUID
    model_version_id: UUID | None

    status: AnalysisResultStatus
    quality_score: float | None
    result_json: dict[str, Any]

    created_at: datetime
    updated_at: datetime


class StudyResultResponse(BaseModel):
    study: StudyDetailResponse
    qc_analysis: QCAnalysisResponse | None

    job: AnalysisJobResponse | None

    result: AnalysisResultResponse | None

    model: ModelVersionResponse | None

    audit: list[AuditEventResponse]
