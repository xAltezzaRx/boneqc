from app.ai.mock import mock_ai_provider
from app.ai.provider import AIProvider
from app.ai.remote import remote_ai_provider
from app.core.config import get_settings


class ProviderNotConfiguredError(RuntimeError):
    pass


_PROVIDERS: dict[str, AIProvider] = {
    "mock": mock_ai_provider,
    "remote": remote_ai_provider,
}


def available_ai_providers() -> list[str]:
    return sorted(_PROVIDERS)


def get_ai_provider(
    name: str | None = None,
) -> AIProvider:
    settings = get_settings()

    selected = (
        name
        if name is not None
        else settings.ai_provider
    )

    selected = selected.strip().lower()

    provider = _PROVIDERS.get(selected)

    if provider is None:
        available = ", ".join(available_ai_providers())

        raise ProviderNotConfiguredError(
            f"AI provider '{selected}' is not configured. "
            f"Available providers: {available}"
        )

    return provider
