from abc import ABC, abstractmethod

from app.ai.contracts import (
    AIAnalysisRequest,
    AIAnalysisResponse,
)


class AIProvider(ABC):
    @abstractmethod
    async def analyze(
        self,
        request: AIAnalysisRequest,
    ) -> AIAnalysisResponse:
        raise NotImplementedError
