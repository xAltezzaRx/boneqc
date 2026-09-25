from abc import ABC, abstractmethod

from app.contracts import (
    AnalyzeRequest,
    AnalyzeResponse,
    ModelInfoResponse,
    Observation,
)
from app.settings import (
    AIEngineSettings,
    get_settings,
)


class InferenceEngine(ABC):
    @abstractmethod
    def model_info(
        self,
    ) -> ModelInfoResponse:
        raise NotImplementedError

    @abstractmethod
    async def analyze(
        self,
        request: AnalyzeRequest,
        preview: bytes,
    ) -> AnalyzeResponse:
        raise NotImplementedError


class MockInferenceEngine(
    InferenceEngine
):
    def __init__(
        self,
        settings: AIEngineSettings,
    ) -> None:
        self.settings = settings

    def model_info(
        self,
    ) -> ModelInfoResponse:
        return ModelInfoResponse(
            backend="mock",
            provider_name=(
                self.settings.provider_name
            ),
            provider_version=(
                self.settings.provider_version
            ),
            model_name=(
                self.settings.model_name
            ),
            model_version=(
                self.settings.model_version
            ),
            model_task=(
                self.settings.model_task
            ),
            git_commit=(
                self.settings.git_commit
            ),
            dataset_version=(
                self.settings.dataset_version
            ),
            weights_hash=(
                self.settings.weights_hash
            ),
            clinical_use=False,
        )

    async def analyze(
        self,
        request: AnalyzeRequest,
        preview: bytes,
    ) -> AnalyzeResponse:
        return AnalyzeResponse(
            provider_name=(
                self.settings.provider_name
            ),
            provider_version=(
                self.settings.provider_version
            ),
            model_name=(
                self.settings.model_name
            ),
            model_version=(
                self.settings.model_version
            ),
            model_task=(
                self.settings.model_task
            ),
            model_git_commit=(
                self.settings.git_commit
            ),
            model_dataset_version=(
                self.settings.dataset_version
            ),
            model_weights_hash=(
                self.settings.weights_hash
            ),
            summary=(
                "Synthetic remote AI Engine response. "
                "No real model inference was performed."
            ),
            observations=[
                Observation(
                    code="POSITIONING",
                    score=0.91,
                    confidence=0.91,
                    message=(
                        "Synthetic remote positioning "
                        "observation."
                    ),
                ),
                Observation(
                    code="ROI_PLACEMENT",
                    score=0.72,
                    confidence=0.72,
                    message=(
                        "Synthetic remote ROI "
                        "observation."
                    ),
                ),
                Observation(
                    code="ARTIFACTS",
                    score=0.88,
                    confidence=0.88,
                    message=(
                        "Synthetic remote artifact "
                        "observation."
                    ),
                ),
            ],
            model_metrics={
                "synthetic": True,
            },
            metadata={
                "remote_mock": True,
                "clinical_use": False,
                "model_backend": "mock",
                "preview_bytes": len(preview),
                "image_rows": (
                    request.dicom_metadata.get(
                        "rows"
                    )
                ),
                "image_columns": (
                    request.dicom_metadata.get(
                        "columns"
                    )
                ),
                "dataset_version": (
                    self.settings.dataset_version
                ),
                "weights_hash": (
                    self.settings.weights_hash
                ),
            },
        )


def create_inference_engine() -> InferenceEngine:
    settings = get_settings()

    if settings.model_backend == "mock":
        return MockInferenceEngine(
            settings
        )

    raise RuntimeError(
        "Unsupported BoneQC AI model backend: "
        f"{settings.model_backend}"
    )
