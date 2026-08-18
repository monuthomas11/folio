from __future__ import annotations

from ...config import settings
from .base import LLMProvider, LLMProviderError
from .mock_provider import MockProvider


def get_llm_provider() -> LLMProvider:
    provider = settings.llm_provider.strip().lower()
    if provider == "mock":
        return MockProvider()
    if provider == "openai":
        if not settings.openai_api_key:
            raise LLMProviderError(
                "LLM_PROVIDER=openai but OPENAI_API_KEY is not set"
            )
        from .openai_provider import OpenAIProvider

        return OpenAIProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model,
        )
    if provider == "gemini":
        if not settings.gemini_api_key:
            raise LLMProviderError(
                "LLM_PROVIDER=gemini but GEMINI_API_KEY is not set"
            )
        from .gemini_provider import GeminiProvider

        return GeminiProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
        )
    raise LLMProviderError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")
