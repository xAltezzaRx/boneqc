from pydantic import BaseModel, Field

from app.models.enums import AnalysisResultStatus


class QualityViolation(BaseModel):
    code: str
    severity: AnalysisResultStatus

    score: float = Field(
        ge=0.0,
        le=1.0,
    )

    threshold: float = Field(
        ge=0.0,
        le=1.0,
    )

    message: str


class QualityEvaluation(BaseModel):
    status: AnalysisResultStatus

    quality_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    engine_version: str

    violations: list[QualityViolation] = Field(
        default_factory=list,
    )

    explanations: list[str] = Field(
        default_factory=list,
    )
