import json
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.audit.service import (
    create_audit_event,
)
from app.auth.security import (
    require_roles,
)
from app.database.session import (
    get_db_session,
)
from app.dataset.snapshots import (
    assign_group_splits,
    manifest_fingerprint,
    split_counts,
    validate_group_safety,
)
from app.ml.export import (
    build_manifest_record,
)
from app.models.dataset_snapshot import (
    DatasetSnapshot,
)
from app.models.enums import (
    AnnotationConsensusStatus,
    AuditEventType,
    UserRole,
)
from app.models.study import Study
from app.models.study_annotation_consensus import (
    StudyAnnotationConsensus,
)
from app.models.user import User
from app.schemas.dataset_snapshot import (
    DatasetSnapshotCreateRequest,
    DatasetSnapshotDetailResponse,
    DatasetSnapshotListResponse,
    DatasetSnapshotResponse,
)


router = APIRouter(
    prefix="/dataset/snapshots",
    tags=["dataset"],
    dependencies=[
        Depends(
            require_roles(
                UserRole.ADMIN,
                UserRole.DOCTOR,
            )
        )
    ],
)


AdminUser = Annotated[
    User,
    Depends(
        require_roles(
            UserRole.ADMIN
        )
    ),
]


async def load_approved_records(
    session: AsyncSession,
    *,
    study_ids: list[UUID]
    | None,
) -> list[dict]:
    query = (
        select(
            Study,
            StudyAnnotationConsensus,
        )
        .join(
            StudyAnnotationConsensus,
            (
                StudyAnnotationConsensus
                .study_id
                == Study.id
            ),
        )
        .where(
            StudyAnnotationConsensus
            .status
            == AnnotationConsensusStatus
            .APPROVED
        )
        .order_by(
            Study.created_at.asc()
        )
    )

    requested: set[
        UUID
    ] | None = None

    if study_ids is not None:
        requested = set(
            study_ids
        )

        if not requested:
            raise HTTPException(
                status_code=(
                    status
                    .HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail={
                    "code":
                        "EMPTY_STUDY_SELECTION",
                },
            )

        query = query.where(
            Study.id.in_(
                requested
            )
        )

    result = await session.execute(
        query
    )

    rows = result.all()

    if requested is not None:
        found = {
            study.id
            for study, _consensus
            in rows
        }

        missing = (
            requested - found
        )

        if missing:
            raise HTTPException(
                status_code=(
                    status
                    .HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail={
                    "code":
                        "STUDY_NOT_APPROVED",
                    "study_ids": sorted(
                        str(item)
                        for item in missing
                    ),
                },
            )

    if not rows:
        raise HTTPException(
            status_code=(
                status
                .HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail={
                "code":
                    "NO_APPROVED_STUDIES",
            },
        )

    records: list[dict] = []

    for study, consensus in rows:
        records.append(
            build_manifest_record(
                study=study,
                consensus=consensus,
            )
        )

    return records


@router.post(
    "",
    response_model=(
        DatasetSnapshotResponse
    ),
    status_code=(
        status.HTTP_201_CREATED
    ),
)
async def create_snapshot(
    request: (
        DatasetSnapshotCreateRequest
    ),
    current_user: AdminUser,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> DatasetSnapshotResponse:
    records = (
        await load_approved_records(
            session,
            study_ids=(
                request.study_ids
            ),
        )
    )

    records = assign_group_splits(
        records,
        seed=request.split_seed,
        train_ratio=(
            request.train_ratio
        ),
        val_ratio=(
            request.val_ratio
        ),
        test_ratio=(
            request.test_ratio
        ),
    )

    validate_group_safety(
        records
    )

    fingerprint = (
        manifest_fingerprint(
            records
        )
    )

    version = (
        "ds-"
        + fingerprint[:12]
    )

    existing = await session.scalar(
        select(
            DatasetSnapshot
        ).where(
            DatasetSnapshot.name
            == "boneqc-qc",
            DatasetSnapshot.version
            == version,
        )
    )

    if existing is not None:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail={
                "code":
                    "DATASET_SNAPSHOT_ALREADY_EXISTS",
                "snapshot_id": str(
                    existing.id
                ),
                "version":
                    existing.version,
            },
        )

    counts = split_counts(
        records
    )

    groups = {
        str(
            record["group_id"]
        )
        for record in records
    }

    study_ids = [
        str(
            record["sample_id"]
        )
        for record in records
    ]

    snapshot = DatasetSnapshot(
        name="boneqc-qc",
        version=version,
        created_by_user_id=(
            current_user.id
        ),
        manifest_fingerprint=(
            fingerprint
        ),
        split_seed=(
            request.split_seed
        ),
        train_ratio=(
            request.train_ratio
        ),
        val_ratio=(
            request.val_ratio
        ),
        test_ratio=(
            request.test_ratio
        ),
        sample_count=len(
            records
        ),
        group_count=len(
            groups
        ),
        train_count=(
            counts["train"]
        ),
        val_count=(
            counts["val"]
        ),
        test_count=(
            counts["test"]
        ),
        study_ids=study_ids,
        manifest=records,
    )

    session.add(snapshot)

    try:
        await session.flush()

        await create_audit_event(
            session,
            event_type=(
                AuditEventType
                .DATASET_SNAPSHOT_CREATED
            ),
            entity_type=(
                "DATASET_SNAPSHOT"
            ),
            entity_id=(
                snapshot.id
            ),
            payload={
                "name":
                    snapshot.name,
                "version":
                    snapshot.version,
                "manifest_fingerprint":
                    fingerprint,
                "sample_count":
                    snapshot.sample_count,
                "group_count":
                    snapshot.group_count,
                "train_count":
                    snapshot.train_count,
                "val_count":
                    snapshot.val_count,
                "test_count":
                    snapshot.test_count,
                "study_ids":
                    snapshot.study_ids,
            },
        )

        await session.commit()

        await session.refresh(
            snapshot
        )

    except IntegrityError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail={
                "code":
                    "DATASET_SNAPSHOT_CONFLICT",
            },
        ) from exc

    return (
        DatasetSnapshotResponse
        .model_validate(snapshot)
    )


@router.get(
    "",
    response_model=(
        DatasetSnapshotListResponse
    ),
)
async def list_snapshots(
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> DatasetSnapshotListResponse:
    total = await session.scalar(
        select(
            func.count()
        ).select_from(
            DatasetSnapshot
        )
    )

    rows = await session.scalars(
        select(
            DatasetSnapshot
        )
        .order_by(
            DatasetSnapshot
            .created_at.desc()
        )
    )

    return (
        DatasetSnapshotListResponse(
            items=[
                DatasetSnapshotResponse
                .model_validate(item)
                for item in rows
            ],
            total=int(total or 0),
        )
    )


@router.get(
    "/{snapshot_id}",
    response_model=(
        DatasetSnapshotDetailResponse
    ),
)
async def get_snapshot(
    snapshot_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> DatasetSnapshotDetailResponse:
    snapshot = await session.get(
        DatasetSnapshot,
        snapshot_id,
    )

    if snapshot is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail={
                "code":
                    "DATASET_SNAPSHOT_NOT_FOUND",
            },
        )

    return (
        DatasetSnapshotDetailResponse
        .model_validate(snapshot)
    )


@router.get(
    "/{snapshot_id}/manifest",
)
async def download_snapshot_manifest(
    snapshot_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> Response:
    snapshot = await session.get(
        DatasetSnapshot,
        snapshot_id,
    )

    if snapshot is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail={
                "code":
                    "DATASET_SNAPSHOT_NOT_FOUND",
            },
        )

    content = (
        "\n".join(
            json.dumps(
                record,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            for record
            in snapshot.manifest
        )
        + "\n"
    )

    return Response(
        content=content,
        media_type=(
            "application/x-ndjson"
        ),
        headers={
            "Content-Disposition": (
                'attachment; filename="'
                + snapshot.version
                + '.jsonl"'
            ),
            "X-BoneQC-Dataset-Fingerprint":
                snapshot
                .manifest_fingerprint,
        },
    )
