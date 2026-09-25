from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import StudyStatus


class StudyCreateResponse(BaseModel):
    id: UUID
    status: StudyStatus
    original_filename: str
    source_object_key: str
    preview_object_key: str | None
    dicom_metadata: dict[str, Any]


class StudySummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: StudyStatus
    original_filename: str
    dicom_metadata: dict[str, Any]
    created_at: datetime


class StudyDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: StudyStatus
    original_filename: str
    source_object_key: str
    preview_object_key: str | None
    dicom_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class StudyListResponse(BaseModel):
    items: list[StudySummaryResponse]
    total: int
    limit: int
    offset: int
