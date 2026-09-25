from app.ai.contracts import (
    AIAnalysisRequest,
    AIAnalysisResponse,
    QualityObservation,
)
from app.ai.provider import AIProvider


class MockAIProvider(AIProvider):
    async def analyze(
        self,
        request: AIAnalysisRequest,
    ) -> AIAnalysisResponse:
        rows = request.dicom_metadata.get("rows")
        columns = request.dicom_metadata.get("columns")

        return AIAnalysisResponse(
            provider_name="mock",
            provider_version="0.2.0",
            model_name="boneqc-mock-qc",
            model_version="0.2.0",
            model_task="quality_control",
            summary=(
                "Synthetic observations generated only to validate "
                "the BoneQC processing pipeline."
            ),
            observations=[
                QualityObservation(
                    code="POSITIONING",
                    score=0.91,
                    confidence=0.91,
                    assessable=True,
                    message=(
                        "Synthetic positioning observation. "
                        "No real model inference was performed."
                    ),
                ),
                QualityObservation(
                    code="ROI_PLACEMENT",
                    score=0.72,
                    confidence=0.72,
                    assessable=True,
                    message=(
                        "Synthetic ROI observation. "
                        "No real model inference was performed."
                    ),
                ),
                QualityObservation(
                    code="ARTIFACTS",
                    score=0.88,
                    confidence=0.88,
                    assessable=True,
                    message=(
                        "Synthetic artifact observation. "
                        "No real model inference was performed."
                    ),
                ),
            ],
            metadata={
                "mock": True,
                "clinical_use": False,
                "image_rows": rows,
                "image_columns": columns,
            },
        )


mock_ai_provider = MockAIProvider()
