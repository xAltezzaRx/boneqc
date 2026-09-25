from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class DatasetSnapshotCreateRequest(
    BaseModel
):
    study_ids: list[
        UUID
    ] | None = None

    split_seed: int = 2026

    train_ratio: float = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
    )

    val_ratio: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
    )

    test_ratio: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
    )

    @model_validator(mode="after")
    def validate_request(
        self,
    ):
        total = (
            self.train_ratio
            + self.val_ratio
            + self.test_ratio
        )

        if abs(total - 1.0) > 1e-9:
            raise ValueError(
                "split ratios must "
                "sum to 1.0"
            )

        if (
            self.study_ids is not None
            and len(self.study_ids)
            != len(
                set(self.study_ids)
            )
        ):
            raise ValueError(
                "study_ids must "
                "be unique"
            )

        return self


class DatasetSnapshotResponse(
    BaseModel
):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID

    name: str
    version: str

    created_by_user_id: UUID | None

    manifest_fingerprint: str

    split_seed: int

    train_ratio: float
    val_ratio: float
    test_ratio: float

    sample_count: int
    group_count: int

    train_count: int
    val_count: int
    test_count: int

    study_ids: list[UUID]

    created_at: datetime
    updated_at: datetime


class DatasetSnapshotDetailResponse(
    DatasetSnapshotResponse
):
    manifest: list[dict]


class DatasetSnapshotListResponse(
    BaseModel
):
    items: list[
        DatasetSnapshotResponse
    ]

    total: int
