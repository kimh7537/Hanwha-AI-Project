"""LLM_PROVIDER 환경변수로 provider 를 고른다.

키가 없거나 provider 이름을 모르면 조용히 mock 으로 떨어진다 — 데모는 절대 멈추지 않는다.
"""

from __future__ import annotations

from app.config import Settings, get_settings
from app.llm.base import LLMProvider, MockProvider


def build_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or get_settings()
    name = (settings.llm_provider or "mock").lower()

    if name in {"", "mock", "none", "off"}:
        return MockProvider()

    if not settings.llm_api_key:
        return MockProvider()

    if name in {"anthropic", "claude"}:
        from app.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(settings)

    if name in {"openai", "gpt"}:
        from app.llm.openai_provider import OpenAIProvider

        return OpenAIProvider(settings)

    return MockProvider()
