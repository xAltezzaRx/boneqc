import unittest

from app.ai.mock import MockAIProvider
from app.ai.registry import (
    ProviderNotConfiguredError,
    available_ai_providers,
    get_ai_provider,
)


class AIProviderRegistryTests(unittest.TestCase):
    def test_mock_is_available(self) -> None:
        self.assertIn(
            "mock",
            available_ai_providers(),
        )

    def test_explicit_mock_provider(self) -> None:
        provider = get_ai_provider("mock")

        self.assertIsInstance(
            provider,
            MockAIProvider,
        )

    def test_provider_name_is_case_insensitive(self) -> None:
        provider = get_ai_provider(" MOCK ")

        self.assertIsInstance(
            provider,
            MockAIProvider,
        )

    def test_unknown_provider_fails(self) -> None:
        with self.assertRaises(
            ProviderNotConfiguredError
        ):
            get_ai_provider("not-configured")


if __name__ == "__main__":
    unittest.main()
