from uuid import UUID

from fastapi import HTTPException, status
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import create_audit_event
from app.models.analysis_job import AnalysisJob
from app.models.enums import (
    AnalysisJobStatus,
    AuditEventType,
    QCAnalysisStatus,
    StudyStatus,
)
from app.models.qc_analysis import QCAnalysis
from app.models.study import Study
from app.queue.service import enqueue_analysis_job


ACTIVE_ANALYSIS_STATUSES = [
    AnalysisJobStatus.QUEUED,
    AnalysisJobStatus.PREPROCESSING,
    AnalysisJobStatus.ANALYZING,
    AnalysisJobStatus.POSTPROCESSING,
]


async def create_analysis_job(
    session: AsyncSession,
    *,
    study_id: UUID,
) -> AnalysisJob:
    study = await session.get(
        Study,
        study_id,
    )

    if study is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "STUDY_NOT_FOUND"},
        )

    if study.status != StudyStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "STUDY_NOT_READY",
                "status": study.status,
            },
        )

    existing = await session.scalar(
        select(AnalysisJob)
        .where(
            AnalysisJob.study_id == study_id,
            AnalysisJob.status.in_(
                ACTIVE_ANALYSIS_STATUSES
            ),
        )
        .order_by(
            AnalysisJob.created_at.desc()
        )
        .limit(1)
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ANALYSIS_ALREADY_ACTIVE",
                "job_id": str(existing.id),
            },
        )

    qc_analysis = QCAnalysis(
        study_id=study_id,
        status=QCAnalysisStatus.QUEUED,
    )

    session.add(qc_analysis)

    try:
        await session.flush()

        qc_analysis_id = qc_analysis.id

        job = AnalysisJob(
            study_id=study_id,
            qc_analysis_id=qc_analysis_id,
            status=AnalysisJobStatus.QUEUED,
        )

        session.add(job)

        await session.flush()

        await create_audit_event(
            session,
            event_type=AuditEventType.ANALYSIS_CREATED,
            entity_type="ANALYSIS_JOB",
            entity_id=job.id,
            study_id=study_id,
            payload={
                "status": AnalysisJobStatus.QUEUED.value,
                "qc_analysis_id": str(qc_analysis_id),
            },
        )

        await session.commit()
        await session.refresh(job)

    except SQLAlchemyError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DATABASE_UNAVAILABLE"},
        ) from exc

    try:
        await enqueue_analysis_job(
            job_id=job.id,
            study_id=study_id,
        )

    except (RedisError, OSError, TimeoutError) as exc:
        job.status = AnalysisJobStatus.FAILED
        job.error_message = "Failed to enqueue analysis job"

        qc_row = await session.get(
            QCAnalysis,
            qc_analysis_id,
        )

        if qc_row is not None:
            qc_row.status = QCAnalysisStatus.FAILED

        await session.commit()

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "QUEUE_UNAVAILABLE",
                "job_id": str(job.id),
            },
        ) from exc

    return job
