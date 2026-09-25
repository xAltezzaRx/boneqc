from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True, slots=True)
class AIEngineSettings:
    model_backend: str
    provider_name: str
    provider_version: str
    model_name: str
    model_version: str
    model_task: str
    git_commit: str | None
    dataset_version: str | None
    weights_hash: str | None


def _optional(
    name: str,
) -> str | None:
    value = getenv(name)

    if value is None:
        return None

    value = value.strip()

    return value or None


def get_settings() -> AIEngineSettings:
    return AIEngineSettings(
        model_backend=getenv(
            "BONEQC_AI_MODEL_BACKEND",
            "mock",
        ).strip().lower(),
        provider_name=getenv(
            "BONEQC_AI_PROVIDER_NAME",
            "remote",
        ),
        provider_version=getenv(
            "BONEQC_AI_PROVIDER_VERSION",
            "0.1.0",
        ),
        model_name=getenv(
            "BONEQC_AI_MODEL_NAME",
            "boneqc-remote-mock-qc",
        ),
        model_version=getenv(
            "BONEQC_AI_MODEL_VERSION",
            "0.1.0",
        ),
        model_task=getenv(
            "BONEQC_AI_MODEL_TASK",
            "quality_control",
        ),
        git_commit=_optional(
            "BONEQC_AI_GIT_COMMIT"
        ),
        dataset_version=_optional(
            "BONEQC_AI_DATASET_VERSION"
        ),
        weights_hash=_optional(
            "BONEQC_AI_WEIGHTS_HASH"
        ),
    )
