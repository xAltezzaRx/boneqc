from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import bind_current_actor, require_roles
from app.models.enums import UserRole
from app.database.session import get_db_session
from app.analysis import service as analysis_service
from app.models.analysis_job import AnalysisJob
from app.models.analysis_result import AnalysisResult
from app.models.qc_analysis import QCAnalysis
from app.models.enums import AnalysisJobStatus, QCAnalysisStatus
from app.queue.service import (
    requeue_analysis_job,
)
from app.schemas.job import AnalysisJobResponse
from app.schemas.result import AnalysisResultResponse

router = APIRouter(tags=["analysis"],
    dependencies=[Depends(bind_current_actor)],
)


@router.post(
    "/studies/{study_id}/analyze",
    response_model=AnalysisJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR))],
)
async def create_analysis_job(
    study_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> AnalysisJobResponse:

    job = await analysis_service.create_analysis_job(
        session,
        study_id=study_id,
    )

    return AnalysisJobResponse.model_validate(job)


@router.get(
    "/jobs/{job_id}",
    response_model=AnalysisJobResponse,
)
async def get_analysis_job(
    job_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> AnalysisJobResponse:
    job = await session.get(AnalysisJob, job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND"},
        )

    return AnalysisJobResponse.model_validate(job)



@router.post(
    "/jobs/{job_id}/retry",
    response_model=AnalysisJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR))],
)
async def retry_analysis_job(
    job_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> AnalysisJobResponse:
    job = await session.scalar(
        select(AnalysisJob)
        .where(
            AnalysisJob.id == job_id
        )
        .with_for_update()
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND"},
        )

    if job.status != AnalysisJobStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "JOB_NOT_FAILED",
                "status": job.status,
            },
        )

    active_statuses = [
        AnalysisJobStatus.QUEUED,
        AnalysisJobStatus.PREPROCESSING,
        AnalysisJobStatus.ANALYZING,
        AnalysisJobStatus.POSTPROCESSING,
    ]

    active_job = await session.scalar(
        select(AnalysisJob)
        .where(
            AnalysisJob.study_id == job.study_id,
            AnalysisJob.id != job.id,
            AnalysisJob.status.in_(active_statuses),
        )
        .order_by(
            AnalysisJob.created_at.desc()
        )
        .limit(1)
    )

    if active_job is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ANALYSIS_ALREADY_ACTIVE",
                "job_id": str(active_job.id),
            },
        )

    previous_attempts = job.attempts
    previous_error = job.error_message
    previous_started_at = job.started_at
    previous_finished_at = job.finished_at

    qc_analysis = None
    previous_qc_status = None
    previous_qc_decision = None
    previous_qc_quality_score = None

    if job.qc_analysis_id is not None:
        qc_analysis = await session.get(
            QCAnalysis,
            job.qc_analysis_id,
        )

        if qc_analysis is not None:
            previous_qc_status = qc_analysis.status
            previous_qc_decision = qc_analysis.decision
            previous_qc_quality_score = qc_analysis.quality_score

            qc_analysis.status = QCAnalysisStatus.QUEUED
            qc_analysis.decision = None
            qc_analysis.quality_score = None

    job.status = AnalysisJobStatus.QUEUED
    job.attempts = 0
    job.error_message = None
    job.started_at = None
    job.finished_at = None

    try:
        await session.commit()
        await session.refresh(job)

    except SQLAlchemyError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DATABASE_UNAVAILABLE"},
        ) from exc

    try:
        await requeue_analysis_job(
            job_id=job.id,
            study_id=job.study_id,
        )

    except (RedisError, OSError, TimeoutError) as exc:
        job.status = AnalysisJobStatus.FAILED
        job.attempts = previous_attempts
        job.error_message = previous_error
        job.started_at = previous_started_at
        job.finished_at = previous_finished_at

        if qc_analysis is not None:
            qc_analysis.status = previous_qc_status
            qc_analysis.decision = previous_qc_decision
            qc_analysis.quality_score = previous_qc_quality_score

        try:
            await session.commit()
            await session.refresh(job)

        except SQLAlchemyError:
            await session.rollback()

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "QUEUE_UNAVAILABLE",
                "job_id": str(job.id),
            },
        ) from exc

    return AnalysisJobResponse.model_validate(job)


@router.get(
    "/jobs/{job_id}/result",
    response_model=AnalysisResultResponse,
    dependencies=[
        Depends(
            require_roles(
                UserRole.ADMIN,
                UserRole.OPERATOR,
            )
        )
    ],
)
async def get_analysis_result(
    job_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> AnalysisResultResponse:
    job = await session.get(AnalysisJob, job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND"},
        )

    result = await session.scalar(
        select(AnalysisResult).where(
            AnalysisResult.job_id == job_id
        )
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "RESULT_NOT_FOUND",
                "job_status": job.status,
            },
        )

    return AnalysisResultResponse.model_validate(result)
