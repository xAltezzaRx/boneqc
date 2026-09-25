import base64

import httpx
from pydantic import ValidationError

from app.ai.contracts import (
    AIAnalysisRequest,
    AIAnalysisResponse,
)
from app.ai.provider import AIProvider
from app.core.config import get_settings


class RemoteAIProviderError(RuntimeError):
    pass


class RemoteAIUnavailableError(RemoteAIProviderError):
    pass


class RemoteAIResponseError(RemoteAIProviderError):
    pass


class RemoteAIProvider(AIProvider):
    def __init__(
        self,
        *,
        base_url: str | None = None,
        token: str | None = None,
        timeout_seconds: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        settings = get_settings()

        self.base_url = (
            base_url or settings.remote_ai_url
        ).rstrip("/")

        self.token = (
            token
            if token is not None
            else settings.remote_ai_token
        )

        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.remote_ai_timeout_seconds
        )

        self.transport = transport

    async def analyze(
        self,
        request: AIAnalysisRequest,
    ) -> AIAnalysisResponse:
        payload = {
            "study_id": str(request.study_id),
            "dicom_metadata": request.dicom_metadata,
            "preview_png_base64": base64.b64encode(
                request.preview_png
            ).decode("ascii"),
        }

        headers = {
            "Content-Type": "application/json",
        }

        if self.token:
            headers["Authorization"] = (
                f"Bearer {self.token}"
            )

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post(
                    f"{self.base_url}/v1/analyze",
                    json=payload,
                    headers=headers,
                )

        except httpx.TimeoutException as exc:
            raise RemoteAIUnavailableError(
                "Remote AI Engine request timed out"
            ) from exc

        except httpx.RequestError as exc:
            raise RemoteAIUnavailableError(
                "Remote AI Engine is unavailable"
            ) from exc

        if not response.is_success:
            raise RemoteAIResponseError(
                "Remote AI Engine returned "
                f"HTTP {response.status_code}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise RemoteAIResponseError(
                "Remote AI Engine returned invalid JSON"
            ) from exc

        try:
            return AIAnalysisResponse.model_validate(data)

        except ValidationError as exc:
            raise RemoteAIResponseError(
                "Remote AI Engine response does not match "
                "AIAnalysisResponse contract"
            ) from exc


remote_ai_provider = RemoteAIProvider()
