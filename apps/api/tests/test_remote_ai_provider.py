import base64
import json
import unittest
from uuid import UUID

import httpx

from app.ai.contracts import AIAnalysisRequest
from app.ai.registry import (
    available_ai_providers,
    get_ai_provider,
)
from app.ai.remote import (
    RemoteAIProvider,
    RemoteAIResponseError,
    RemoteAIUnavailableError,
)


STUDY_ID = UUID(
    "11111111-2222-3333-4444-555555555555"
)


def request_data() -> AIAnalysisRequest:
    return AIAnalysisRequest(
        study_id=STUDY_ID,
        dicom_metadata={
            "rows": 256,
            "columns": 256,
            "modality": "DX",
        },
        preview_png=b"boneqc-preview",
    )


def valid_response() -> dict:
    return {
        "provider_name": "remote",
        "provider_version": "0.1.0",
        "model_name": "boneqc-test-model",
        "model_version": "1.0.0",
        "model_task": "quality_control",
        "summary": "Synthetic remote inference result.",
        "observations": [
            {
                "code": "POSITIONING",
                "score": 0.91,
                "confidence": 0.89,
                "assessable": True,
                "message": "Synthetic test observation.",
            }
        ],
        "metadata": {
            "mock_remote": True,
            "clinical_use": False,
        },
    }


class RemoteAIProviderTests(
    unittest.IsolatedAsyncioTestCase
):
    async def test_successful_response(self) -> None:
        async def handler(
            request: httpx.Request,
        ) -> httpx.Response:
            return httpx.Response(
                200,
                json=valid_response(),
            )

        provider = RemoteAIProvider(
            base_url="http://test-ai",
            transport=httpx.MockTransport(handler),
        )

        result = await provider.analyze(
            request_data()
        )

        self.assertEqual(
            result.provider_name,
            "remote",
        )
        self.assertEqual(
            result.model_name,
            "boneqc-test-model",
        )
        self.assertEqual(
            len(result.observations),
            1,
        )

    async def test_request_payload(self) -> None:
        async def handler(
            request: httpx.Request,
        ) -> httpx.Response:
            payload = json.loads(
                request.content.decode()
            )

            self.assertEqual(
                payload["study_id"],
                str(STUDY_ID),
            )

            self.assertEqual(
                payload["dicom_metadata"]["rows"],
                256,
            )

            preview = base64.b64decode(
                payload["preview_png_base64"]
            )

            self.assertEqual(
                preview,
                b"boneqc-preview",
            )

            self.assertEqual(
                request.url.path,
                "/v1/analyze",
            )

            return httpx.Response(
                200,
                json=valid_response(),
            )

        provider = RemoteAIProvider(
            base_url="http://test-ai/",
            transport=httpx.MockTransport(handler),
        )

        await provider.analyze(request_data())

    async def test_bearer_token(self) -> None:
        async def handler(
            request: httpx.Request,
        ) -> httpx.Response:
            self.assertEqual(
                request.headers.get(
                    "Authorization"
                ),
                "Bearer secret-token",
            )

            return httpx.Response(
                200,
                json=valid_response(),
            )

        provider = RemoteAIProvider(
            base_url="http://test-ai",
            token="secret-token",
            transport=httpx.MockTransport(handler),
        )

        await provider.analyze(request_data())

    async def test_timeout(self) -> None:
        async def handler(
            request: httpx.Request,
        ) -> httpx.Response:
            raise httpx.ReadTimeout(
                "timeout",
                request=request,
            )

        provider = RemoteAIProvider(
            base_url="http://test-ai",
            transport=httpx.MockTransport(handler),
        )

        with self.assertRaises(
            RemoteAIUnavailableError
        ):
            await provider.analyze(
                request_data()
            )

    async def test_unavailable(self) -> None:
        async def handler(
            request: httpx.Request,
        ) -> httpx.Response:
            raise httpx.ConnectError(
                "connection failed",
                request=request,
            )

        provider = RemoteAIProvider(
            base_url="http://test-ai",
            transport=httpx.MockTransport(handler),
        )

        with self.assertRaises(
            RemoteAIUnavailableError
        ):
            await provider.analyze(
                request_data()
            )

    async def test_http_error(self) -> None:
        async def handler(
            request: httpx.Request,
        ) -> httpx.Response:
            return httpx.Response(
                500,
                json={"error": "inference failed"},
            )

        provider = RemoteAIProvider(
            base_url="http://test-ai",
            transport=httpx.MockTransport(handler),
        )

        with self.assertRaises(
            RemoteAIResponseError
        ):
            await provider.analyze(
                request_data()
            )

    async def test_invalid_json(self) -> None:
        async def handler(
            request: httpx.Request,
        ) -> httpx.Response:
            return httpx.Response(
                200,
                content=b"not-json",
            )

        provider = RemoteAIProvider(
            base_url="http://test-ai",
            transport=httpx.MockTransport(handler),
        )

        with self.assertRaises(
            RemoteAIResponseError
        ):
            await provider.analyze(
                request_data()
            )

    async def test_invalid_contract(self) -> None:
        async def handler(
            request: httpx.Request,
        ) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "provider_name": "remote",
                    "unexpected": True,
                },
            )

        provider = RemoteAIProvider(
            base_url="http://test-ai",
            transport=httpx.MockTransport(handler),
        )

        with self.assertRaises(
            RemoteAIResponseError
        ):
            await provider.analyze(
                request_data()
            )

    async def test_registry_exposes_remote(
        self,
    ) -> None:
        self.assertIn(
            "remote",
            available_ai_providers(),
        )

        provider = get_ai_provider("remote")

        self.assertIsInstance(
            provider,
            RemoteAIProvider,
        )


if __name__ == "__main__":
    unittest.main()
