from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import require_roles
from app.models.enums import UserRole
from app.database.session import get_db_session
from app.models.analysis_job import AnalysisJob
from app.models.analysis_result import AnalysisResult
from app.models.audit_event import AuditEvent
from app.models.model_version import ModelVersion
from app.models.qc_analysis import QCAnalysis
from app.models.study import Study
from app.schemas.audit import AuditEventResponse
from app.schemas.job import AnalysisJobResponse
from app.schemas.model_version import ModelVersionResponse
from app.schemas.qc_analysis import QCAnalysisResponse
from app.schemas.result import (
    AnalysisResultResponse,
    StudyResultResponse,
)
from app.schemas.study import StudyDetailResponse


router = APIRouter(
    prefix="/studies",
    tags=["results"],
    dependencies=[
        Depends(
            require_roles(
                UserRole.ADMIN,
                UserRole.OPERATOR,
            )
        )
    ],
)


@router.get(
    "/{study_id}/result",
    response_model=StudyResultResponse,
)
async def get_study_result(
    study_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> StudyResultResponse:
    study = await session.get(
        Study,
        study_id,
    )

    if study is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "STUDY_NOT_FOUND"},
        )

    qc_analysis = await session.scalar(
        select(QCAnalysis)
        .where(
            QCAnalysis.study_id == study_id
        )
        .order_by(
            QCAnalysis.created_at.desc()
        )
        .limit(1)
    )

    if qc_analysis is not None:
        job = await session.scalar(
            select(AnalysisJob)
            .where(
                AnalysisJob.qc_analysis_id
                == qc_analysis.id
            )
            .order_by(
                AnalysisJob.created_at.desc()
            )
            .limit(1)
        )
    else:
        job = await session.scalar(
            select(AnalysisJob)
            .where(
                AnalysisJob.study_id == study_id
            )
            .order_by(
                AnalysisJob.created_at.desc()
            )
            .limit(1)
        )

    result = None

    if job is not None:
        result = await session.scalar(
            select(AnalysisResult)
            .where(
                AnalysisResult.job_id == job.id
            )
            .limit(1)
        )

    if (
        result is None
        and qc_analysis is None
    ):
        result = await session.scalar(
            select(AnalysisResult)
            .where(
                AnalysisResult.study_id == study_id
            )
            .order_by(
                AnalysisResult.created_at.desc()
            )
            .limit(1)
        )

    model = None

    if (
        result is not None
        and result.model_version_id
    ):
        model = await session.get(
            ModelVersion,
            result.model_version_id,
        )

    audit_rows = await session.scalars(
        select(AuditEvent)
        .where(
            AuditEvent.study_id == study_id
        )
        .order_by(
            AuditEvent.created_at.asc()
        )
    )

    return StudyResultResponse(
        study=StudyDetailResponse.model_validate(
            study
        ),
        qc_analysis=(
            QCAnalysisResponse.model_validate(
                qc_analysis
            )
            if qc_analysis
            else None
        ),
        job=(
            AnalysisJobResponse.model_validate(job)
            if job
            else None
        ),
        result=(
            AnalysisResultResponse.model_validate(result)
            if result
            else None
        ),
        model=(
            ModelVersionResponse.model_validate(model)
            if model
            else None
        ),
        audit=[
            AuditEventResponse.model_validate(event)
            for event in audit_rows
        ],
    )
