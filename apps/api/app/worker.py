import asyncio
import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.ai.contracts import AIAnalysisRequest, AIAnalysisResponse
from app.audit.service import create_audit_event
from app.ai.registry import get_ai_provider
from app.ai.remote import RemoteAIUnavailableError
from app.ai.c7_gateway import (
    C7GatewayBusyError,
    C7GatewayUnavailableError,
    c7_gateway_client,
)
from app.ai.c7_product import (
    save_c7_analysis_result,
)
from app.dicom.anatomy_guard import (
    evaluate_dicom_anatomy,
)
from app.dicom.anatomy_guard_result import (
    save_anatomy_guard_result,
)
from app.dicom.input_sanity import (
    evaluate_dicom_bytes,
)
from app.dicom.input_sanity_result import (
    save_input_sanity_result,
)
from app.core.config import get_settings
from app.database.session import AsyncSessionLocal
from app.decision.contracts import FinalDecision
from app.decision.resolver import decision_resolver
from app.quality.contracts import QualityEvaluation
from app.quality.engine import quality_engine
from app.uncertainty.contracts import UncertaintyEvaluation
from app.uncertainty.engine import uncertainty_engine
from app.models.analysis_job import AnalysisJob
from app.models.analysis_result import AnalysisResult
from app.models.qc_analysis import QCAnalysis
from app.models.enums import (
    AnalysisJobStatus,
    AnalysisResultStatus,
    AuditEventType,
    QCAnalysisStatus,
)
from app.models.study import Study
from app.model_registry.service import resolve_model_version
from app.queue.client import redis_client
from app.queue.heartbeat import run_worker_heartbeat
from app.queue.service import (
    ANALYSIS_QUEUE,
    ANALYSIS_RETRY_DELAY_SECONDS,
    MAX_ANALYSIS_ATTEMPTS,
    enqueue_analysis_job,
    enqueue_dead_letter,
)
from app.storage.service import storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger("boneqc.worker")


async def update_job_status(
    job_id: UUID,
    status: AnalysisJobStatus,
) -> bool:
    async with AsyncSessionLocal() as session:
        job = await session.get(AnalysisJob, job_id)

        if job is None:
            logger.error("job_not_found job_id=%s", job_id)
            return False

        qc_analysis = None

        if job.qc_analysis_id is not None:
            qc_analysis = await session.get(
                QCAnalysis,
                job.qc_analysis_id,
            )

        if status == AnalysisJobStatus.PREPROCESSING:
            job.attempts += 1
            job.started_at = datetime.now(timezone.utc)
            job.error_message = None

        if status in {
            AnalysisJobStatus.COMPLETED,
            AnalysisJobStatus.FAILED,
        }:
            job.finished_at = datetime.now(timezone.utc)

        if (
            qc_analysis is not None
            and status in {
                AnalysisJobStatus.PREPROCESSING,
                AnalysisJobStatus.ANALYZING,
                AnalysisJobStatus.POSTPROCESSING,
            }
        ):
            qc_analysis.status = QCAnalysisStatus.RUNNING

        if (
            qc_analysis is not None
            and status == AnalysisJobStatus.FAILED
        ):
            qc_analysis.status = QCAnalysisStatus.FAILED

        job.status = status
        await session.commit()

    logger.info(
        "job_status job_id=%s status=%s",
        job_id,
        status.value,
    )

    return True


async def mark_failed(
    job_id: UUID,
    message: str,
) -> None:
    try:
        async with AsyncSessionLocal() as session:
            job = await session.get(AnalysisJob, job_id)

            if job is None:
                return

            job.status = AnalysisJobStatus.FAILED
            job.error_message = message[:2000]
            job.finished_at = datetime.now(timezone.utc)

            if job.qc_analysis_id is not None:
                qc_analysis = await session.get(
                    QCAnalysis,
                    job.qc_analysis_id,
                )

                if qc_analysis is not None:
                    qc_analysis.status = QCAnalysisStatus.FAILED

            await session.commit()

    except SQLAlchemyError:
        logger.exception(
            "failed_to_mark_job_failed job_id=%s",
            job_id,
        )


async def retry_or_fail_job(
    *,
    job_id: UUID,
    study_id: UUID,
    message: str,
) -> None:
    async with AsyncSessionLocal() as session:
        job = await session.get(AnalysisJob, job_id)

        if job is None:
            logger.error(
                "retry_job_missing job_id=%s",
                job_id,
            )
            return

        qc_analysis = None

        if job.qc_analysis_id is not None:
            qc_analysis = await session.get(
                QCAnalysis,
                job.qc_analysis_id,
            )

        attempts = job.attempts

        if attempts >= MAX_ANALYSIS_ATTEMPTS:
            job.status = AnalysisJobStatus.FAILED
            job.error_message = message[:2000]
            job.finished_at = datetime.now(timezone.utc)

            if qc_analysis is not None:
                qc_analysis.status = QCAnalysisStatus.FAILED

            await session.commit()

            await enqueue_dead_letter(
                job_id=job_id,
                study_id=study_id,
                attempts=attempts,
                error_message=message,
                failure_type="retry_exhausted",
            )

            logger.error(
                "job_retry_exhausted job_id=%s attempts=%s",
                job_id,
                attempts,
            )

            return

        job.status = AnalysisJobStatus.QUEUED
        job.error_message = message[:2000]
        job.finished_at = None

        if qc_analysis is not None:
            qc_analysis.status = QCAnalysisStatus.QUEUED

        await session.commit()

    logger.warning(
        "job_retry_scheduled job_id=%s attempt=%s next_attempt=%s",
        job_id,
        attempts,
        attempts + 1,
    )

    await asyncio.sleep(
        ANALYSIS_RETRY_DELAY_SECONDS
    )

    await enqueue_analysis_job(
        job_id=job_id,
        study_id=study_id,
    )


async def fail_job_to_dead_letter(
    *,
    job_id: UUID,
    study_id: UUID,
    message: str,
    failure_type: str,
) -> None:
    await mark_failed(
        job_id,
        message,
    )

    async with AsyncSessionLocal() as session:
        job = await session.get(AnalysisJob, job_id)

        attempts = (
            job.attempts
            if job is not None
            else 0
        )

    await enqueue_dead_letter(
        job_id=job_id,
        study_id=study_id,
        attempts=attempts,
        error_message=message,
        failure_type=failure_type,
    )


async def save_analysis_result(
    *,
    job_id: UUID,
    study_id: UUID,
    ai_response: AIAnalysisResponse,
    model_version_id: UUID,
    quality: QualityEvaluation,
    uncertainty: UncertaintyEvaluation,
    final_decision: FinalDecision,
) -> None:
    payload = {
        "provider": {
            "name": ai_response.provider_name,
            "version": ai_response.provider_version,
            "summary": ai_response.summary,
        },
        "model": {
            "name": ai_response.model_name,
            "version": ai_response.model_version,
            "task": ai_response.model_task,
            "git_commit": ai_response.model_git_commit,
            "dataset_version": (
                ai_response.model_dataset_version
            ),
            "weights_hash": (
                ai_response.model_weights_hash
            ),
            "metrics": ai_response.model_metrics,
        },
        "observations": [
            observation.model_dump(mode="json")
            for observation in ai_response.observations
        ],
        "provider_metadata": ai_response.metadata,
        "quality": quality.model_dump(mode="json"),
        "uncertainty": uncertainty.model_dump(mode="json"),
        "final_decision": final_decision.model_dump(mode="json"),
    }

    async with AsyncSessionLocal() as session:
        job = await session.get(
            AnalysisJob,
            job_id,
        )

        result = await session.scalar(
            select(AnalysisResult).where(
                AnalysisResult.job_id == job_id
            )
        )

        if result is None:
            result = AnalysisResult(
                study_id=study_id,
                job_id=job_id,
                model_version_id=model_version_id,
                status=final_decision.status,
                quality_score=quality.quality_score,
                result_json=payload,
            )
            session.add(result)

        else:
            result.model_version_id = model_version_id
            result.status = final_decision.status
            result.quality_score = quality.quality_score
            result.result_json = payload

        if (
            job is not None
            and job.qc_analysis_id is not None
        ):
            qc_analysis = await session.get(
                QCAnalysis,
                job.qc_analysis_id,
            )

            if qc_analysis is not None:
                qc_analysis.decision = final_decision.status.value
                qc_analysis.quality_score = quality.quality_score

                if final_decision.status in {
                    AnalysisResultStatus.REVIEW,
                    AnalysisResultStatus.CANNOT_ASSESS,
                }:
                    qc_analysis.status = (
                        QCAnalysisStatus.REVIEW_REQUIRED
                    )
                else:
                    qc_analysis.status = (
                        QCAnalysisStatus.COMPLETED
                    )

        await session.commit()


async def process_job(payload: str) -> None:
    data = json.loads(payload)

    job_id = UUID(data["job_id"])
    study_id = UUID(data["study_id"])

    logger.info(
        "job_received job_id=%s study_id=%s",
        job_id,
        study_id,
    )

    try:
        async with AsyncSessionLocal() as session:
            job = await session.get(AnalysisJob, job_id)

            if job is None:
                logger.error("job_missing job_id=%s", job_id)
                return

            if job.study_id != study_id:
                raise ValueError(
                    "Queue study_id does not match AnalysisJob"
                )

            if job.status != AnalysisJobStatus.QUEUED:
                logger.warning(
                    "job_not_queued job_id=%s status=%s",
                    job_id,
                    job.status.value,
                )
                return

            study = await session.get(Study, study_id)

            if study is None:
                raise ValueError("Study does not exist")

            if not study.preview_object_key:
                raise ValueError(
                    "Study does not contain preview_object_key"
                )

            dicom_metadata = dict(study.dicom_metadata or {})
            preview_object_key = study.preview_object_key
            source_object_key = study.source_object_key

        if not await update_job_status(
            job_id,
            AnalysisJobStatus.PREPROCESSING,
        ):
            return

        async with AsyncSessionLocal() as session:
            await create_audit_event(
                session,
                event_type=AuditEventType.ANALYSIS_STARTED,
                entity_type="ANALYSIS_JOB",
                entity_id=job_id,
                study_id=study_id,
                payload={
                    "status": "PREPROCESSING",
                },
            )
            await session.commit()

        settings = get_settings()

        if (
            settings.ai_provider
            .strip()
            .lower()
            == "c7"
        ):
            dicom_bytes = await asyncio.to_thread(
                storage.get_bytes,
                key=source_object_key,
            )

            input_sanity = evaluate_dicom_bytes(
                dicom_bytes
            )

            sanity_cannot_assess_reasons = {
                "DEGENERATE_UNIFORM_PIXELS",
                "SYNTHETIC_NOISE_PATTERN",
            }

            if (
                not input_sanity.assessable
                and input_sanity.reason
                in sanity_cannot_assess_reasons
            ):
                await update_job_status(
                    job_id,
                    AnalysisJobStatus.POSTPROCESSING,
                )

                await save_input_sanity_result(
                    job_id=job_id,
                    study_id=study_id,
                    sanity=input_sanity,
                )

                async with AsyncSessionLocal() as session:
                    await create_audit_event(
                        session,
                        event_type=(
                            AuditEventType
                            .DECISION_CREATED
                        ),
                        entity_type=(
                            "ANALYSIS_JOB"
                        ),
                        entity_id=job_id,
                        study_id=study_id,
                        payload={
                            "decision":
                                (
                                    AnalysisResultStatus
                                    .CANNOT_ASSESS
                                    .value
                                ),

                            "decision_source":
                                (
                                    "input_sanity_gate"
                                ),

                            "sanity_reason":
                                input_sanity.reason,

                            "c7_invoked":
                                False,
                        },
                    )

                    await session.commit()

                await update_job_status(
                    job_id,
                    AnalysisJobStatus.COMPLETED,
                )

                logger.info(
                    "job_completed_input_sanity "
                    "job_id=%s "
                    "result_status=%s "
                    "reason=%s "
                    "c7_invoked=false",
                    job_id,
                    (
                        AnalysisResultStatus
                        .CANNOT_ASSESS
                        .value
                    ),
                    input_sanity.reason,
                )

                return

            if not input_sanity.assessable:
                raise ValueError(
                    "Input sanity evaluation failed "
                    "outside the supported "
                    "CANNOT_ASSESS boundary: "
                    f"{input_sanity.reason}"
                )

            anatomy_guard = evaluate_dicom_anatomy(
                dicom_bytes
            )

            if not anatomy_guard.supported:
                await update_job_status(
                    job_id,
                    AnalysisJobStatus.POSTPROCESSING,
                )

                await save_anatomy_guard_result(
                    job_id=job_id,
                    study_id=study_id,
                    anatomy=anatomy_guard,
                )

                async with AsyncSessionLocal() as session:
                    await create_audit_event(
                        session,
                        event_type=(
                            AuditEventType
                            .DECISION_CREATED
                        ),
                        entity_type=(
                            "ANALYSIS_JOB"
                        ),
                        entity_id=job_id,
                        study_id=study_id,
                        payload={
                            "decision":
                                (
                                    AnalysisResultStatus
                                    .CANNOT_ASSESS
                                    .value
                                ),

                            "decision_source":
                                "anatomy_guard",

                            "anatomy_reason":
                                anatomy_guard.reason,

                            "anatomy_evidence":
                                anatomy_guard.evidence,

                            "c7_invoked":
                                False,
                        },
                    )

                    await session.commit()

                await update_job_status(
                    job_id,
                    AnalysisJobStatus.COMPLETED,
                )

                logger.info(
                    "job_completed_anatomy_guard "
                    "job_id=%s "
                    "result_status=%s "
                    "reason=%s "
                    "c7_invoked=false",
                    job_id,
                    (
                        AnalysisResultStatus
                        .CANNOT_ASSESS
                        .value
                    ),
                    anatomy_guard.reason,
                )

                return

            await update_job_status(
                job_id,
                AnalysisJobStatus.ANALYZING,
            )

            async with AsyncSessionLocal() as session:
                await create_audit_event(
                    session,
                    event_type=(
                        AuditEventType.AI_PROVIDER_SELECTED
                    ),
                    entity_type="ANALYSIS_JOB",
                    entity_id=job_id,
                    study_id=study_id,
                    payload={
                        "provider": "C7GatewayClient",
                        "authoritative": True,
                    },
                )
                await session.commit()

            gateway_response = await (
                c7_gateway_client.analyze_dicom(
                    dicom_bytes
                )
            )

            raw_result = (
                gateway_response.get("result")
                or {}
            )

            async with AsyncSessionLocal() as session:
                await create_audit_event(
                    session,
                    event_type=(
                        AuditEventType.AI_ANALYSIS_COMPLETED
                    ),
                    entity_type="ANALYSIS_JOB",
                    entity_id=job_id,
                    study_id=study_id,
                    payload={
                        "provider": "frozen_c7",
                        "model_name": "boneqc-c7-final",
                        "model_version": "runtime-v1",
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
                        "processing_status": (
                            raw_result.get(
                                "processing_status"
                            )
                        ),
                        "quality_class": (
                            raw_result.get(
                                "quality_class"
                            )
                        ),
                    },
                )
                await session.commit()

            await update_job_status(
                job_id,
                AnalysisJobStatus.POSTPROCESSING,
            )

            (
                c7_status,
                c7_quality_prob,
            ) = await save_c7_analysis_result(
                job_id=job_id,
                study_id=study_id,
                gateway_response=gateway_response,
            )

            async with AsyncSessionLocal() as session:
                await create_audit_event(
                    session,
                    event_type=(
                        AuditEventType.DECISION_CREATED
                    ),
                    entity_type="ANALYSIS_JOB",
                    entity_id=job_id,
                    study_id=study_id,
                    payload={
                        "decision": c7_status.value,
                        "quality_prob": (
                            c7_quality_prob
                        ),
                        "decision_source": (
                            "frozen_c7_authoritative"
                        ),
                        "product_side_recalculation": False,
                    },
                )
                await session.commit()

            await update_job_status(
                job_id,
                AnalysisJobStatus.COMPLETED,
            )

            logger.info(
                "job_completed_c7 "
                "job_id=%s "
                "result_status=%s "
                "quality_prob=%s",
                job_id,
                c7_status.value,
                c7_quality_prob,
            )

            return

        preview_png = await asyncio.to_thread(
            storage.get_bytes,
            key=preview_object_key,
        )

        await update_job_status(
            job_id,
            AnalysisJobStatus.ANALYZING,
        )

        ai_request = AIAnalysisRequest(
            study_id=study_id,
            dicom_metadata=dicom_metadata,
            preview_png=preview_png,
        )

        ai_provider = get_ai_provider()

        async with AsyncSessionLocal() as session:
            await create_audit_event(
                session,
                event_type=AuditEventType.AI_PROVIDER_SELECTED,
                entity_type="ANALYSIS_JOB",
                entity_id=job_id,
                study_id=study_id,
                payload={
                    "provider": ai_provider.__class__.__name__,
                },
            )
            await session.commit()

        ai_response = await ai_provider.analyze(
            ai_request
        )

        async with AsyncSessionLocal() as session:
            await create_audit_event(
                session,
                event_type=AuditEventType.AI_ANALYSIS_COMPLETED,
                entity_type="ANALYSIS_JOB",
                entity_id=job_id,
                study_id=study_id,
                payload={
                    "provider": ai_response.provider_name,
                    "provider_version": ai_response.provider_version,
                    "model_name": ai_response.model_name,
                    "model_version": ai_response.model_version,
                    "model_git_commit": (
                        ai_response.model_git_commit
                    ),
                    "dataset_version": (
                        ai_response.model_dataset_version
                    ),
                    "weights_hash": (
                        ai_response.model_weights_hash
                    ),
                    "observations": len(
                        ai_response.observations
                    ),
                },
            )
            await session.commit()

        if (
            ai_response.model_name is None
            or ai_response.model_version is None
            or ai_response.model_task is None
        ):
            raise ValueError(
                "AI provider did not return complete model identity"
            )

        async with AsyncSessionLocal() as session:
            model_version = await resolve_model_version(
                session,
                name=ai_response.model_name,
                version=ai_response.model_version,
                task=ai_response.model_task,
                git_commit=(
                    ai_response.model_git_commit
                ),
                dataset_version=(
                    ai_response.model_dataset_version
                ),
                weights_hash=(
                    ai_response.model_weights_hash
                ),
                metrics=ai_response.model_metrics,
            )

            model_version_id = model_version.id

        quality = quality_engine.evaluate(
            ai_response
        )

        uncertainty = uncertainty_engine.evaluate(
            ai_response
        )

        final_decision = decision_resolver.resolve(
            quality=quality,
            uncertainty=uncertainty,
        )

        async with AsyncSessionLocal() as session:
            await create_audit_event(
                session,
                event_type=AuditEventType.DECISION_CREATED,
                entity_type="ANALYSIS_JOB",
                entity_id=job_id,
                study_id=study_id,
                payload={
                    "decision": final_decision.status,
                    "reasons": final_decision.reasons,
                    "quality_score": quality.quality_score,
                    "uncertainty": uncertainty.decision,
                },
            )
            await session.commit()

        await update_job_status(
            job_id,
            AnalysisJobStatus.POSTPROCESSING,
        )

        await save_analysis_result(
            job_id=job_id,
            study_id=study_id,
            ai_response=ai_response,
            model_version_id=model_version_id,
            quality=quality,
            uncertainty=uncertainty,
            final_decision=final_decision,
        )

        await update_job_status(
            job_id,
            AnalysisJobStatus.COMPLETED,
        )

        logger.info(
            "job_completed job_id=%s result_status=%s score=%s",
            job_id,
            final_decision.status.value,
            quality.quality_score,
        )

    except (
        RemoteAIUnavailableError,
        C7GatewayUnavailableError,
        C7GatewayBusyError,
    ) as exc:
        logger.warning(
            "job_transient_failure job_id=%s error=%s",
            job_id,
            exc,
        )

        await retry_or_fail_job(
            job_id=job_id,
            study_id=study_id,
            message=str(exc),
        )

    except Exception as exc:
        logger.exception(
            "job_failed job_id=%s",
            job_id,
        )

        await fail_job_to_dead_letter(
            job_id=job_id,
            study_id=study_id,
            message=str(exc),
            failure_type=type(exc).__name__,
        )


async def run_worker() -> None:
    logger.info(
        "worker_started queue=%s",
        ANALYSIS_QUEUE,
    )

    while True:
        try:
            item = await redis_client.blpop(
                ANALYSIS_QUEUE,
                timeout=2,
            )

            if item is None:
                continue

            _, payload = item

            try:
                await process_job(payload)

            except (
                json.JSONDecodeError,
                KeyError,
                TypeError,
                ValueError,
            ):
                logger.exception(
                    "invalid_queue_payload payload=%r",
                    payload,
                )

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception("worker_loop_error")
            await asyncio.sleep(2)


async def main() -> None:
    heartbeat_task = asyncio.create_task(
        run_worker_heartbeat()
    )

    try:
        await run_worker()

    finally:
        heartbeat_task.cancel()

        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

        await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
