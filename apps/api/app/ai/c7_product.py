from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.models.analysis_job import AnalysisJob
from app.models.analysis_result import AnalysisResult
from app.models.enums import (
    AnalysisResultStatus,
    QCAnalysisStatus,
)
from app.models.qc_analysis import QCAnalysis
from app.model_registry.service import (
    resolve_model_version,
)


C7_MODEL_NAME = "boneqc-c7-final"
C7_MODEL_VERSION = "runtime-v1"
C7_MODEL_TASK = "quality_control"


class C7ProductResultError(RuntimeError):
    pass


def _split_violation_types(
    value: str | None,
) -> list[str]:
    if not value:
        return []

    result: list[str] = []

    for item in value.split(";"):
        normalized = item.strip()

        if (
            normalized
            and normalized not in result
        ):
            result.append(normalized)

    return result


def _normalize_c7_result(
    gateway_response: dict[str, Any],
) -> tuple[
    AnalysisResultStatus,
    float | None,
    dict[str, Any],
]:
    if gateway_response.get("status") != "Success":
        raise C7ProductResultError(
            "C7 gateway did not return Success"
        )

    raw_result = gateway_response.get("result")

    if not isinstance(raw_result, dict):
        raise C7ProductResultError(
            "C7 gateway result is missing"
        )

    processing_status = raw_result.get(
        "processing_status"
    )

    if processing_status == "UnsupportedAnatomy":
        return (
            AnalysisResultStatus.CANNOT_ASSESS,
            None,
            raw_result,
        )

    if processing_status != "Success":
        raise C7ProductResultError(
            "C7 processing_status is not Success: "
            f"{processing_status!r}"
        )

    quality_class = raw_result.get(
        "quality_class"
    )

    if (
        type(quality_class) is not int
        or quality_class not in {0, 1}
    ):
        raise C7ProductResultError(
            "C7 quality_class must be 0 or 1"
        )

    quality_prob_raw = raw_result.get(
        "quality_prob"
    )

    quality_prob: float | None = None

    if quality_prob_raw is not None:
        try:
            quality_prob = float(
                quality_prob_raw
            )
        except (TypeError, ValueError) as exc:
            raise C7ProductResultError(
                "C7 quality_prob is invalid"
            ) from exc

        if not 0.0 <= quality_prob <= 1.0:
            raise C7ProductResultError(
                "C7 quality_prob is outside [0, 1]"
            )

    violation_type = raw_result.get(
        "violation_type"
    )

    if (
        violation_type is not None
        and not isinstance(
            violation_type,
            str,
        )
    ):
        raise C7ProductResultError(
            "C7 violation_type is invalid"
        )

    if isinstance(violation_type, str):
        violation_type = (
            violation_type.strip()
            or None
        )

    violation_types = _split_violation_types(
        violation_type
    )

    if (
        quality_class == 0
        and violation_types
    ):
        raise C7ProductResultError(
            "C7 contract inconsistency: "
            "quality_class=0 with violation"
        )

    if (
        quality_class == 1
        and not violation_types
    ):
        raise C7ProductResultError(
            "C7 contract inconsistency: "
            "quality_class=1 without violation"
        )

    status = (
        AnalysisResultStatus.PASS
        if quality_class == 0
        else AnalysisResultStatus.FAIL
    )

    return (
        status,
        quality_prob,
        raw_result,
    )


async def save_c7_analysis_result(
    *,
    job_id: UUID,
    study_id: UUID,
    gateway_response: dict[str, Any],
) -> tuple[
    AnalysisResultStatus,
    float | None,
]:
    (
        result_status,
        quality_prob,
        raw_result,
    ) = _normalize_c7_result(
        gateway_response
    )

    routing_metadata = gateway_response.get(
        "_boneqc_routing"
    )

    if not isinstance(
        routing_metadata,
        dict,
    ):
        routing_metadata = {}

    violation_type = raw_result.get(
        "violation_type"
    )

    violation_types = _split_violation_types(
        violation_type
        if isinstance(
            violation_type,
            str,
        )
        else None
    )

    violations: list[dict[str, Any]] = [
        {
            "code": item,
            "message": item,
        }
        for item in violation_types
    ]

    if result_status == AnalysisResultStatus.PASS:
        reasons = [
            (
                "Frozen C7 authoritative result: "
                "quality_class=0."
            )
        ]

    elif result_status == AnalysisResultStatus.FAIL:
        reasons = [
            (
                "Frozen C7 authoritative result: "
                "quality_class=1."
            )
        ]

        for item in violation_types:
            reasons.append(
                f"Violation: {item}"
            )

    else:
        reasons = [
            (
                "Frozen C7 could not assess "
                "the anatomical region."
            )
        ]

    payload: dict[str, Any] = {
        "provider": {
            "name": "frozen_c7",
            "version": gateway_response.get(
                "gateway_version"
            ),
            "summary": (
                "Frozen C7 competition QC runtime."
            ),
        },
        "observations": [],
        "provider_metadata": {
            "clinical_use": False,
            "authoritative": True,
            "product_side_recalculation": False,
            "inference_node": (
                routing_metadata.get(
                    "inference_node"
                )
            ),
            "fallback_used": bool(
                routing_metadata.get(
                    "fallback_used",
                    False,
                )
            ),
            "primary_failure_type": (
                routing_metadata.get(
                    "primary_failure_type"
                )
            ),
            "runtime_image": (
                gateway_response.get(
                    "runtime_image"
                )
            ),
            "gateway_version": (
                gateway_response.get(
                    "gateway_version"
                )
            ),
            "input_sha256": (
                gateway_response.get(
                    "input_sha256"
                )
            ),
            "elapsed_seconds": (
                gateway_response.get(
                    "elapsed_seconds"
                )
            ),
        },
        "quality": {
            "status": result_status.value,
            "quality_score": None,
            "quality_prob": quality_prob,
            "quality_class": raw_result.get(
                "quality_class"
            ),
            "anatomical_region": (
                raw_result.get(
                    "anatomical_region"
                )
            ),
            "violation_type": violation_type,
            "violations": violations,
        },
        "uncertainty": {
            "decision": "NOT_RECALCULATED",
            "mean_confidence": None,
            "minimum_confidence": None,
            "reasons": [
                (
                    "Frozen C7 output is used "
                    "without product-side "
                    "uncertainty recalculation."
                )
            ],
        },
        "final_decision": {
            "status": result_status.value,
            "reasons": reasons,
            "resolver_version": (
                "frozen-c7-authoritative-v1"
            ),
        },
        "c7_gateway": {
            "status": gateway_response.get(
                "status"
            ),
            "gateway_version": (
                gateway_response.get(
                    "gateway_version"
                )
            ),
            "runtime_image": (
                gateway_response.get(
                    "runtime_image"
                )
            ),
            "input_sha256": (
                gateway_response.get(
                    "input_sha256"
                )
            ),
            "elapsed_seconds": (
                gateway_response.get(
                    "elapsed_seconds"
                )
            ),
        },
        "c7_result": raw_result,
    }

    async with AsyncSessionLocal() as session:
        model = await resolve_model_version(
            session,
            name=C7_MODEL_NAME,
            version=C7_MODEL_VERSION,
            task=C7_MODEL_TASK,
            metrics={
                "frozen_runtime": True,
                "clinical_use": False,
            },
        )

        job = await session.get(
            AnalysisJob,
            job_id,
        )

        result = await session.scalar(
            select(
                AnalysisResult
            ).where(
                AnalysisResult.job_id
                == job_id
            )
        )

        if result is None:
            result = AnalysisResult(
                study_id=study_id,
                job_id=job_id,
                model_version_id=model.id,
                status=result_status,
                quality_score=None,
                result_json=payload,
            )
            session.add(result)

        else:
            result.model_version_id = (
                model.id
            )
            result.status = result_status
            result.quality_score = None
            result.result_json = payload

        if (
            job is not None
            and job.qc_analysis_id
            is not None
        ):
            qc_analysis = await session.get(
                QCAnalysis,
                job.qc_analysis_id,
            )

            if qc_analysis is not None:
                qc_analysis.decision = (
                    result_status.value
                )

                qc_analysis.quality_score = (
                    None
                )

                if (
                    result_status
                    == AnalysisResultStatus.CANNOT_ASSESS
                ):
                    qc_analysis.status = (
                        QCAnalysisStatus.REVIEW_REQUIRED
                    )
                else:
                    qc_analysis.status = (
                        QCAnalysisStatus.COMPLETED
                    )

        await session.commit()

    return (
        result_status,
        quality_prob,
    )
