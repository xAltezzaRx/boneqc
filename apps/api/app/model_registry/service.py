from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ModelVersionStatus
from app.models.model_version import ModelVersion


class ModelVersionNotFoundError(RuntimeError):
    pass


class ModelVersionMetadataConflictError(RuntimeError):
    pass


def reconcile_model_metadata(
    model: ModelVersion,
    *,
    task: str,
    git_commit: str | None = None,
    dataset_version: str | None = None,
    weights_hash: str | None = None,
    metrics: dict[str, Any] | None = None,
) -> bool:
    if model.task != task:
        raise ModelVersionMetadataConflictError(
            "Model task conflict for "
            f"{model.name}:{model.version}: "
            f"registry={model.task!r}, "
            f"provider={task!r}"
        )

    changed = False

    optional_fields = {
        "git_commit": git_commit,
        "dataset_version": dataset_version,
        "weights_hash": weights_hash,
    }

    for field, incoming in optional_fields.items():
        if incoming is None:
            continue

        current = getattr(
            model,
            field,
        )

        if current is None:
            setattr(
                model,
                field,
                incoming,
            )
            changed = True
            continue

        if current != incoming:
            raise ModelVersionMetadataConflictError(
                "Model provenance conflict for "
                f"{model.name}:{model.version} "
                f"field={field}: "
                f"registry={current!r}, "
                f"provider={incoming!r}"
            )

    incoming_metrics = metrics or {}
    current_metrics = dict(
        model.metrics or {}
    )

    for key, value in incoming_metrics.items():
        if (
            key in current_metrics
            and current_metrics[key] != value
        ):
            raise ModelVersionMetadataConflictError(
                "Model metric conflict for "
                f"{model.name}:{model.version} "
                f"metric={key}: "
                f"registry={current_metrics[key]!r}, "
                f"provider={value!r}"
            )

        if key not in current_metrics:
            current_metrics[key] = value
            changed = True

    if changed:
        model.metrics = current_metrics

    return changed


async def get_or_create_model_version(
    session: AsyncSession,
    *,
    name: str,
    version: str,
    task: str,
    status: ModelVersionStatus = ModelVersionStatus.EXPERIMENTAL,
    git_commit: str | None = None,
    dataset_version: str | None = None,
    weights_hash: str | None = None,
    metrics: dict[str, Any] | None = None,
) -> ModelVersion:
    existing = await session.scalar(
        select(ModelVersion).where(
            ModelVersion.name == name,
            ModelVersion.version == version,
        )
    )

    if existing is not None:
        return existing

    model = ModelVersion(
        name=name,
        version=version,
        task=task,
        status=status,
        git_commit=git_commit,
        dataset_version=dataset_version,
        weights_hash=weights_hash,
        metrics=metrics or {},
    )

    session.add(model)

    try:
        await session.commit()
        await session.refresh(model)
        return model

    except IntegrityError:
        await session.rollback()

        existing = await session.scalar(
            select(ModelVersion).where(
                ModelVersion.name == name,
                ModelVersion.version == version,
            )
        )

        if existing is None:
            raise

        return existing


async def require_model_version(
    session: AsyncSession,
    *,
    name: str,
    version: str,
) -> ModelVersion:
    model = await session.scalar(
        select(ModelVersion).where(
            ModelVersion.name == name,
            ModelVersion.version == version,
        )
    )

    if model is None:
        raise ModelVersionNotFoundError(
            "Model version is not registered: "
            f"{name}:{version}"
        )

    return model


async def resolve_model_version(
    session: AsyncSession,
    *,
    name: str,
    version: str,
    task: str,
    git_commit: str | None = None,
    dataset_version: str | None = None,
    weights_hash: str | None = None,
    metrics: dict[str, Any] | None = None,
) -> ModelVersion:
    model = await session.scalar(
        select(ModelVersion).where(
            ModelVersion.name == name,
            ModelVersion.version == version,
        )
    )

    if model is None:
        model = ModelVersion(
            name=name,
            version=version,
            task=task,
            status=ModelVersionStatus.EXPERIMENTAL,
            git_commit=git_commit,
            dataset_version=dataset_version,
            weights_hash=weights_hash,
            metrics=metrics or {},
        )

        session.add(model)

        try:
            await session.commit()
            await session.refresh(model)
            return model

        except IntegrityError:
            await session.rollback()

            model = await session.scalar(
                select(ModelVersion).where(
                    ModelVersion.name == name,
                    ModelVersion.version == version,
                )
            )

            if model is None:
                raise

    changed = reconcile_model_metadata(
        model,
        task=task,
        git_commit=git_commit,
        dataset_version=dataset_version,
        weights_hash=weights_hash,
        metrics=metrics,
    )

    if changed:
        await session.commit()
        await session.refresh(model)

    return model
