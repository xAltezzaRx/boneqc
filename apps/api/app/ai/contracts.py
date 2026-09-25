from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AIAnalysisRequest(BaseModel):
    study_id: UUID
    dicom_metadata: dict[str, Any]
    preview_png: bytes


class QualityObservation(BaseModel):
    code: str

    score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    assessable: bool = True
    message: str


class AIAnalysisResponse(BaseModel):
    provider_name: str
    provider_version: str

    model_name: str | None = None
    model_version: str | None = None
    model_task: str | None = None

    model_git_commit: str | None = None
    model_dataset_version: str | None = None
    model_weights_hash: str | None = None

    model_metrics: dict[str, Any] = Field(
        default_factory=dict,
    )

    summary: str
    observations: list[QualityObservation]

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
