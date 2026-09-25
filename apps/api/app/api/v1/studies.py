import asyncio
from uuid import UUID, uuid4

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.privacy.pseudonym import derive_privacy_group_id
from app.auth.security import bind_current_actor, require_roles
from app.models.enums import UserRole
from app.core.config import get_settings
from app.audit.service import create_audit_event
from app.database.session import get_db_session
from app.dicom.processor import (
    DicomProcessingError,
    DicomProcessor,
    InvalidDicomFileError,
    MissingPixelDataError,
    PixelDecodeError,
    UnsafePixelDataError,
)
from app.models.enums import AuditEventType, StudyStatus
from app.models.study import Study
from app.schemas.study import (
    StudyCreateResponse,
    StudyDetailResponse,
    StudyListResponse,
    StudySummaryResponse,
)
from app.storage.service import storage

router = APIRouter(
    prefix="/studies",
    tags=["studies"],
    dependencies=[Depends(bind_current_actor)],
)

processor = DicomProcessor()


@router.post(
    "",
    response_model=StudyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR))],
)
async def create_study(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
) -> StudyCreateResponse:
    settings = get_settings()

    data = await file.read(settings.max_upload_bytes + 1)

    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "FILE_TOO_LARGE",
                "max_bytes": settings.max_upload_bytes,
            },
        )

    try:
        result = processor.process(data)

        privacy_group_id = derive_privacy_group_id(
            data,
            secret=(
                settings.pseudonym_secret
                .get_secret_value()
            ),
        )

    except MissingPixelDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "MISSING_PIXEL_DATA",
                "message": str(exc),
            },
        ) from exc

    except PixelDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "PIXEL_DECODE_ERROR",
                "message": str(exc),
            },
        ) from exc

    except UnsafePixelDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "UNSAFE_PIXEL_DATA",
                "message": str(exc),
            },
        ) from exc

    except InvalidDicomFileError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_DICOM",
                "message": str(exc),
            },
        ) from exc

    except DicomProcessingError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "DICOM_PROCESSING_ERROR",
                "message": str(exc),
            },
        ) from exc

    study_id = uuid4()

    source_key = f"studies/{study_id}/source.dcm"
    preview_key = f"studies/{study_id}/preview.png"

    uploaded_keys: list[str] = []

    try:
        await asyncio.to_thread(
            storage.put_bytes,
            key=source_key,
            data=result.deidentified_dicom,
            content_type="application/dicom",
        )
        uploaded_keys.append(source_key)

        await asyncio.to_thread(
            storage.put_bytes,
            key=preview_key,
            data=result.preview_png,
            content_type="image/png",
        )
        uploaded_keys.append(preview_key)

    except (BotoCoreError, ClientError, OSError, TimeoutError) as exc:
        for key in uploaded_keys:
            try:
                await asyncio.to_thread(
                    storage.delete_object,
                    key=key,
                )
            except Exception:
                pass

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "OBJECT_STORAGE_UNAVAILABLE",
            },
        ) from exc

    # Never persist the user-supplied filename:
    # it may itself contain patient-identifying information.
    filename = "study.dcm"

    study = Study(
        id=study_id,
        status=StudyStatus.READY,
        privacy_group_id=privacy_group_id,
        original_filename=filename,
        source_object_key=source_key,
        preview_object_key=preview_key,
        dicom_metadata=result.metadata,
    )

    session.add(study)

    try:
        # The Study row must be flushed before audit_events:
        # audit_events.study_id has a foreign key to studies.id.
        await session.flush()

        await create_audit_event(
            session,
            event_type=AuditEventType.DICOM_DEIDENTIFIED,
            entity_type="STUDY",
            entity_id=study.id,
            study_id=study.id,
            payload=result.deidentification,
        )

        await create_audit_event(
            session,
            event_type=AuditEventType.STUDY_CREATED,
            entity_type="STUDY",
            entity_id=study.id,
            study_id=study.id,
            payload={
                "status": study.status,
                "filename": study.original_filename,
                "source_object_key": study.source_object_key,
            },
        )

        await session.commit()

    except SQLAlchemyError as exc:
        await session.rollback()

        for key in uploaded_keys:
            try:
                await asyncio.to_thread(
                    storage.delete_object,
                    key=key,
                )
            except Exception:
                pass

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "DATABASE_UNAVAILABLE",
            },
        ) from exc

    return StudyCreateResponse(
        id=study.id,
        status=study.status,
        original_filename=study.original_filename,
        source_object_key=study.source_object_key,
        preview_object_key=study.preview_object_key,
        dicom_metadata=study.dicom_metadata,
    )



@router.get(
    "",
    response_model=StudyListResponse,
)
async def list_studies(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> StudyListResponse:
    total = await session.scalar(
        select(func.count()).select_from(Study)
    )

    result = await session.execute(
        select(Study)
        .order_by(Study.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    studies = result.scalars().all()

    return StudyListResponse(
        items=[
            StudySummaryResponse.model_validate(study)
            for study in studies
        ],
        total=int(total or 0),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{study_id}",
    response_model=StudyDetailResponse,
)
async def get_study(
    study_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> StudyDetailResponse:
    study = await session.get(Study, study_id)

    if study is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "STUDY_NOT_FOUND",
            },
        )

    return StudyDetailResponse.model_validate(study)


@router.get(
    "/{study_id}/preview",
    response_class=Response,
)
async def get_study_preview(
    study_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    study = await session.get(Study, study_id)

    if study is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "STUDY_NOT_FOUND",
            },
        )

    if study.preview_object_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PREVIEW_NOT_FOUND",
            },
        )

    try:
        preview = await asyncio.to_thread(
            storage.get_bytes,
            key=study.preview_object_key,
        )

    except ClientError as exc:
        error_code = str(
            exc.response.get("Error", {}).get("Code", "")
        )

        if error_code in {
            "404",
            "NoSuchKey",
            "NoSuchObject",
            "NotFound",
        }:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "PREVIEW_NOT_FOUND",
                },
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "OBJECT_STORAGE_UNAVAILABLE",
            },
        ) from exc

    except (BotoCoreError, OSError, TimeoutError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "OBJECT_STORAGE_UNAVAILABLE",
            },
        ) from exc

    return Response(
        content=preview,
        media_type="image/png",
        headers={
            "Cache-Control": "private, max-age=60",
        },
    )
