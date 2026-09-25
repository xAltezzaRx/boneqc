from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.database.session import (
    AsyncSessionLocal,
)
from app.dicom.input_sanity import (
    InputSanityResult,
)
from app.models.analysis_job import (
    AnalysisJob,
)
from app.models.analysis_result import (
    AnalysisResult,
)
from app.models.enums import (
    AnalysisResultStatus,
    QCAnalysisStatus,
)
from app.models.qc_analysis import (
    QCAnalysis,
)


INPUT_SANITY_PROVIDER_VERSION = "1.0"


def build_input_sanity_payload(
    sanity: InputSanityResult,
) -> dict:
    reason = (
        sanity.reason
        or "INPUT_NOT_ASSESSABLE"
    )

    human_reason = (
        "Автоматическая оценка невозможна: "
        "входное изображение не прошло "
        "детерминированную техническую "
        "проверку перед запуском Frozen C7."
    )

    return {
        "provider": {
            "name":
                "input_sanity_gate",

            "version":
                INPUT_SANITY_PROVIDER_VERSION,

            "summary": (
                "Deterministic pre-inference "
                "input sanity gate."
            ),
        },

        "observations": [],

        "provider_metadata": {
            "clinical_use":
                False,

            "authoritative":
                False,

            "product_side_gate":
                True,

            "product_side_recalculation":
                False,

            "c7_invoked":
                False,

            "sanity_reason":
                reason,

            "sanity_metrics":
                sanity.metrics,
        },

        "quality": {
            "status":
                AnalysisResultStatus
                .CANNOT_ASSESS
                .value,

            "quality_score":
                None,

            "quality_prob":
                None,

            "quality_class":
                None,

            "anatomical_region":
                None,

            "violation_type":
                None,

            "violations": [],
        },

        "uncertainty": {
            "decision":
                "CANNOT_ASSESS",

            "mean_confidence":
                None,

            "minimum_confidence":
                None,

            "reasons": [
                (
                    "Input sanity gate rejected "
                    "the image before Frozen C7 "
                    "inference."
                ),
                reason,
            ],
        },

        "final_decision": {
            "status":
                AnalysisResultStatus
                .CANNOT_ASSESS
                .value,

            "reasons": [
                human_reason,
                reason,
            ],

            "resolver_version":
                "input-sanity-gate-v1",
        },
    }


async def save_input_sanity_result(
    *,
    job_id: UUID,
    study_id: UUID,
    sanity: InputSanityResult,
) -> None:
    payload = build_input_sanity_payload(
        sanity
    )

    async with AsyncSessionLocal() as session:
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
                model_version_id=None,
                status=(
                    AnalysisResultStatus
                    .CANNOT_ASSESS
                ),
                quality_score=None,
                result_json=payload,
            )

            session.add(
                result
            )

        else:
            result.model_version_id = None

            result.status = (
                AnalysisResultStatus
                .CANNOT_ASSESS
            )

            result.quality_score = None
            result.result_json = payload

        job = await session.get(
            AnalysisJob,
            job_id,
        )

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
                    AnalysisResultStatus
                    .CANNOT_ASSESS
                    .value
                )

                qc_analysis.quality_score = None

                qc_analysis.status = (
                    QCAnalysisStatus
                    .REVIEW_REQUIRED
                )

        await session.commit()
