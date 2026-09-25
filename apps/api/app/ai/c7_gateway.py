from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings


class C7GatewayError(RuntimeError):
    pass


class C7GatewayUnavailableError(C7GatewayError):
    pass


class C7GatewayBusyError(C7GatewayError):
    pass


class C7GatewayResponseError(C7GatewayError):
    pass


class C7GatewayClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        token_file: str | None = None,
        timeout_seconds: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        settings = get_settings()

        self.base_url = (
            base_url
            or settings.c7_gateway_url
        ).rstrip("/")

        self.token_file = Path(
            token_file
            or settings.c7_gateway_token_file
        )

        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.c7_gateway_timeout_seconds
        )

        self.transport = transport

    def _read_token(self) -> str:
        try:
            token = self.token_file.read_text(
                encoding="utf-8",
            ).strip()
        except OSError as exc:
            raise C7GatewayUnavailableError(
                "C7 gateway token file is unavailable"
            ) from exc

        if not token:
            raise C7GatewayUnavailableError(
                "C7 gateway token is empty"
            )

        return token

    async def health_ready(
        self,
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                timeout=10.0,
                transport=self.transport,
            ) as client:
                response = await client.get(
                    f"{self.base_url}/health/ready",
                )
        except httpx.RequestError as exc:
            raise C7GatewayUnavailableError(
                "C7 gateway is unavailable"
            ) from exc

        if not response.is_success:
            raise C7GatewayResponseError(
                "C7 gateway readiness returned "
                f"HTTP {response.status_code}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise C7GatewayResponseError(
                "C7 gateway readiness returned invalid JSON"
            ) from exc

        if not isinstance(data, dict):
            raise C7GatewayResponseError(
                "C7 gateway readiness returned invalid payload"
            )

        return data

    async def analyze_dicom(
        self,
        dicom_bytes: bytes,
    ) -> dict[str, Any]:
        if not dicom_bytes:
            raise ValueError(
                "DICOM payload must not be empty"
            )

        token = self._read_token()

        input_sha256 = hashlib.sha256(
            dicom_bytes
        ).hexdigest()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/dicom",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post(
                    f"{self.base_url}/v1/analyze",
                    content=dicom_bytes,
                    headers=headers,
                )

        except httpx.TimeoutException as exc:
            raise C7GatewayUnavailableError(
                "C7 gateway inference timed out"
            ) from exc

        except httpx.RequestError as exc:
            raise C7GatewayUnavailableError(
                "C7 gateway is unavailable"
            ) from exc

        if response.status_code == 409:
            raise C7GatewayBusyError(
                "C7 gateway is busy"
            )

        if not response.is_success:
            raise C7GatewayResponseError(
                "C7 gateway returned "
                f"HTTP {response.status_code}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise C7GatewayResponseError(
                "C7 gateway returned invalid JSON"
            ) from exc

        if not isinstance(data, dict):
            raise C7GatewayResponseError(
                "C7 gateway returned invalid payload"
            )

        returned_sha256 = data.get(
            "input_sha256"
        )

        if (
            returned_sha256 is not None
            and returned_sha256 != input_sha256
        ):
            raise C7GatewayResponseError(
                "C7 gateway input SHA256 mismatch"
            )

        return data


class C7FailoverClient:
    def __init__(
        self,
        *,
        primary: C7GatewayClient | None = None,
        fallback: C7GatewayClient | None = None,
        fallback_enabled: bool | None = None,
    ) -> None:
        settings = get_settings()

        self.primary = (
            primary
            or C7GatewayClient(
                base_url=settings.c7_gateway_url,
            )
        )

        self.fallback = (
            fallback
            or C7GatewayClient(
                base_url=(
                    settings.c7_fallback_gateway_url
                ),
            )
        )

        self.fallback_enabled = (
            fallback_enabled
            if fallback_enabled is not None
            else settings.c7_fallback_enabled
        )

    @staticmethod
    def _with_routing(
        payload: dict[str, Any],
        *,
        inference_node: str,
        fallback_used: bool,
        primary_failure_type: str | None = None,
    ) -> dict[str, Any]:
        result = dict(payload)

        result["_boneqc_routing"] = {
            "inference_node": inference_node,
            "fallback_used": fallback_used,
            "primary_failure_type": (
                primary_failure_type
            ),
        }

        return result

    async def health_ready(
        self,
    ) -> dict[str, Any]:
        return await self.primary.health_ready()

    async def analyze_dicom(
        self,
        dicom_bytes: bytes,
    ) -> dict[str, Any]:
        try:
            response = (
                await self.primary.analyze_dicom(
                    dicom_bytes
                )
            )

        except C7GatewayUnavailableError:
            if not self.fallback_enabled:
                raise

            fallback_response = (
                await self.fallback.analyze_dicom(
                    dicom_bytes
                )
            )

            return self._with_routing(
                fallback_response,
                inference_node="gtx1060",
                fallback_used=True,
                primary_failure_type=(
                    "unavailable"
                ),
            )

        return self._with_routing(
            response,
            inference_node="rtx3080",
            fallback_used=False,
        )


c7_gateway_client = C7FailoverClient()
