from typing import Literal

from pydantic import BaseModel, Field


class UncertaintyEvaluation(BaseModel):
    decision: Literal[
        "ACCEPT",
        "REVIEW",
        "CANNOT_ASSESS",
    ]

    minimum_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    mean_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    engine_version: str

    reasons: list[str] = Field(
        default_factory=list,
    )
