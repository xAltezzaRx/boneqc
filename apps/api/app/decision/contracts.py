from pydantic import BaseModel, Field

from app.models.enums import AnalysisResultStatus


class FinalDecision(BaseModel):
    status: AnalysisResultStatus
    resolver_version: str

    reasons: list[str] = Field(
        default_factory=list,
    )
