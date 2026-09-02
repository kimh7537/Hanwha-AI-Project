"""provider 전환과 fallback (docs/08-api-and-env.md).

'키가 없거나 호출이 실패해도 데모는 멈추지 않는다' 를 기계적으로 보장한다.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.config import Settings
from app.llm.base import LLMProvider, LLMUnavailable, MockProvider, RunContext
from app.llm.factory import build_provider
from app.models.contracts import PresentationRequest
from app.services.pipeline import build_document_from_text, generate


class _BrokenProvider(LLMProvider):
    """항상 실패하는 provider. 실제 장애 상황을 흉내 낸다."""

    name = "anthropic"
    available = True

    def complete_json(self, system: str, user: str, max_tokens: int = 2000) -> dict[str, Any]:
        raise LLMUnavailable("네트워크 오류")


class _JunkProvider(LLMProvider):
    """계약과 맞지 않는 JSON 을 돌려주는 provider."""

    name = "openai"
    available = True

    def complete_json(self, system: str, user: str, max_tokens: int = 2000) -> dict[str, Any]:
        return {"완전히": "다른 모양"}


def _request() -> PresentationRequest:
    return PresentationRequest(
        audience="customer",
        purpose="technical_explanation",
        duration_minutes=5,
        keywords=["정확도"],
        style="persuasive",
        slide_count=5,
    )


def test_defaults_to_mock_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    provider = build_provider(Settings())
    assert provider.name == "mock"
    assert provider.available is False


def test_unknown_provider_falls_back_to_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "존재하지않는provider")
    monkeypatch.setenv("LLM_API_KEY", "dummy")

    assert build_provider(Settings()).name == "mock"


def test_mock_provider_reports_unavailable() -> None:
    ctx = RunContext(provider=MockProvider())
    assert ctx.call_json("테스트", "system", "user") is None
    # mock 은 장애가 아니라 기본 모드다. fallback 으로 기록하지 않는다.
    assert ctx.fallback_used is False


def test_llm_failure_records_fallback_and_completes(sample_text: str) -> None:
    ctx = RunContext(provider=_BrokenProvider())
    document = build_document_from_text(sample_text, "sample_document.txt")

    response = generate(document, _request(), ctx)

    assert response.meta.fallback_used is True
    assert "네트워크 오류" in response.meta.fallback_reason
    assert response.meta.provider == "anthropic"

    # 장애가 나도 결과물은 완전해야 한다
    assert response.slide_deck.slides
    assert response.presentation_support.scripts
    assert response.verification_report is not None
    for slide in response.slide_deck.slides:
        assert slide.source_refs


def test_contract_violating_response_falls_back(sample_text: str) -> None:
    ctx = RunContext(provider=_JunkProvider())
    document = build_document_from_text(sample_text, "sample_document.txt")

    response = generate(document, _request(), ctx)

    assert response.meta.fallback_used is True
    assert "계약" in response.meta.fallback_reason
    assert response.slide_deck.slides


def test_successful_run_reports_no_fallback(sample_text: str) -> None:
    document = build_document_from_text(sample_text, "sample_document.txt")
    response = generate(document, _request(), RunContext(provider=MockProvider()))

    assert response.meta.provider == "mock"
    assert response.meta.fallback_used is False
