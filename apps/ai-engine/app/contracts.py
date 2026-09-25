from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    study_id: UUID
    dicom_metadata: dict[str, Any]
    preview_png_base64: str


class Observation(BaseModel):
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


class AnalyzeResponse(BaseModel):
    provider_name: str
    provider_version: str

    model_name: str
    model_version: str
    model_task: str

    model_git_commit: str | None = None
    model_dataset_version: str | None = None
    model_weights_hash: str | None = None

    summary: str
    observations: list[Observation]

    model_metrics: dict[str, Any] = Field(
        default_factory=dict,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class ModelInfoResponse(BaseModel):
    backend: str

    provider_name: str
    provider_version: str

    model_name: str
    model_version: str
    model_task: str

    git_commit: str | None = None
    dataset_version: str | None = None
    weights_hash: str | None = None

    clinical_use: bool = False
