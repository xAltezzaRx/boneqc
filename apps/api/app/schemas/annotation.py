from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.models.enums import (
    AnnotationConsensusStatus,
)


TOKEN_PATTERN = (
    r"^[A-Z][A-Z0-9_]{1,63}$"
)


class NormalizedPoint(BaseModel):
    x: float = Field(
        ge=0.0,
        le=1.0,
    )

    y: float = Field(
        ge=0.0,
        le=1.0,
    )


class AnnotationGeometry(BaseModel):
    kind: Literal[
        "POINT",
        "LINE",
        "POLYLINE",
        "BOX",
        "POLYGON",
    ]

    label: str = Field(
        min_length=2,
        max_length=64,
        pattern=TOKEN_PATTERN,
    )

    points: list[
        NormalizedPoint
    ] = Field(
        min_length=1,
        max_length=64,
    )

    @model_validator(mode="after")
    def validate_geometry(
        self,
    ):
        count = len(
            self.points
        )

        expected = {
            "POINT": (1, 1),
            "LINE": (2, 2),
            "BOX": (2, 2),
            "POLYLINE": (2, 64),
            "POLYGON": (3, 64),
        }

        minimum, maximum = expected[
            self.kind
        ]

        if not (
            minimum
            <= count
            <= maximum
        ):
            raise ValueError(
                f"{self.kind} requires "
                f"{minimum}..{maximum} points"
            )

        return self


class ClinicalLabel(BaseModel):
    code: str = Field(
        min_length=2,
        max_length=64,
        pattern=TOKEN_PATTERN,
    )

    assessable: bool = True

    class_label: str | None = Field(
        default=None,
        min_length=2,
        max_length=64,
        pattern=TOKEN_PATTERN,
    )

    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    comment: str | None = Field(
        default=None,
        max_length=2000,
    )

    geometry: list[
        AnnotationGeometry
    ] = Field(
        default_factory=list,
        max_length=64,
    )

    @field_validator(
        "code",
        "class_label",
        mode="before",
    )
    @classmethod
    def reject_whitespace(
        cls,
        value,
    ):
        if (
            isinstance(value, str)
            and value != value.strip()
        ):
            raise ValueError(
                "surrounding whitespace "
                "is not allowed"
            )

        return value

    @model_validator(mode="after")
    def validate_assessment(
        self,
    ):
        if (
            self.assessable
            and self.class_label is None
        ):
            raise ValueError(
                "assessable label requires "
                "class_label"
            )

        if (
            not self.assessable
            and self.class_label is not None
        ):
            raise ValueError(
                "unassessable label must not "
                "contain class_label"
            )

        return self


class AnnotationCreateRequest(BaseModel):
    schema_version: str = Field(
        min_length=1,
        max_length=32,
    )

    labels: list[ClinicalLabel] = Field(
        min_length=1,
        max_length=100,
    )

    @field_validator(
        "schema_version"
    )
    @classmethod
    def validate_schema_version(
        cls,
        value: str,
    ) -> str:
        if value != value.strip():
            raise ValueError(
                "surrounding whitespace "
                "is not allowed"
            )

        return value


class StudyAnnotationResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID
    study_id: UUID
    reviewer_user_id: UUID | None

    schema_version: str
    labels: list[ClinicalLabel]

    created_at: datetime
    updated_at: datetime


class StudyAnnotationListResponse(BaseModel):
    items: list[
        StudyAnnotationResponse
    ]

    total: int


class MyAnnotationStatusResponse(
    BaseModel
):
    reviewed: bool


class ConsensusCreateRequest(BaseModel):
    schema_version: str = Field(
        min_length=1,
        max_length=32,
    )

    source_annotation_ids: list[
        UUID
    ] = Field(
        min_length=2,
        max_length=20,
    )

    labels: list[
        ClinicalLabel
    ] = Field(
        min_length=1,
        max_length=100,
    )

    @field_validator(
        "source_annotation_ids"
    )
    @classmethod
    def reject_duplicate_sources(
        cls,
        value: list[UUID],
    ) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError(
                "source annotation IDs "
                "must be unique"
            )

        return value


class StudyAnnotationConsensusResponse(
    BaseModel
):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID
    study_id: UUID

    created_by_user_id: UUID | None
    reviewed_by_user_id: UUID | None

    schema_version: str

    status: AnnotationConsensusStatus

    source_annotation_ids: list[UUID]

    labels: list[ClinicalLabel]

    reviewed_at: datetime | None

    created_at: datetime
    updated_at: datetime


class StudyAnnotationConsensusListResponse(
    BaseModel
):
    items: list[
        StudyAnnotationConsensusResponse
    ]

    total: int
