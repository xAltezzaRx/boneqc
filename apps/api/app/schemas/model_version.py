from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import ModelVersionStatus


class ModelVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    version: str
    task: str
    status: ModelVersionStatus

    git_commit: str | None
    dataset_version: str | None
    weights_hash: str | None

    metrics: dict[str, Any]

    created_at: datetime
    updated_at: datetime


class ModelVersionListResponse(BaseModel):
    items: list[ModelVersionResponse]
    total: int
    limit: int
    offset: int
