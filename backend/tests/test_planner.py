"""모듈 C: SlideDeck 구성 (docs/04-slide-planner.md)."""

from __future__ import annotations

import pytest

from app.llm.base import RunContext
from app.models.contracts import PresentationRequest, SourceAnalysis
from app.services.audience import transform
from app.services.planner import plan, resolve_slide_count


def _request(**overrides) -> PresentationRequest:
    payload = {
        "audience": "customer",
        "purpose": "technical_explanation",
        "duration_minutes": 5,
        "keywords": ["정확도", "도입 효과"],
        "style": "persuasive",
        "preserve_original_terms": True,
    }
    payload.update(overrides)
    return PresentationRequest(**payload)


def _plan(analysis: SourceAnalysis, request: PresentationRequest):
    ctx = RunContext()
    return plan(transform(analysis, request, ctx), analysis, request, ctx)


@pytest.mark.parametrize(
    ("duration", "expected"), [(3, 4), (5, 5), (10, 7)]
)
def test_slide_count_follows_duration(duration: int, expected: int) -> None:
    assert resolve_slide_count(_request(duration_minutes=duration, slide_count=None)) == expected


def test_explicit_slide_count_is_clamped() -> None:
    assert resolve_slide_count(_request(slide_count=99)) == 10
    assert resolve_slide_count(_request(slide_count=1)) == 3


def test_every_slide_has_evidence(analysis: SourceAnalysis) -> None:
    """데모 성공 기준 4번. 근거 없는 슬라이드는 만들지 않는다."""
    deck = _plan(analysis, _request())
    known = {e.id for e in analysis.source_evidence}

    assert deck.slides
    for slide in deck.slides:
        assert slide.source_refs, f"{slide.id} 에 근거가 없습니다"
        assert set(slide.source_refs) <= known


def test_slides_have_readable_text(analysis: SourceAnalysis) -> None:
    """화면에 그대로 읽히는 문장에 말줄임표가 남으면 자료가 깨져 보인다."""
    deck = _plan(analysis, _request())
    for slide in deck.slides:
        assert slide.title
        assert slide.takeaway
        assert "…" not in slide.takeaway
        assert slide.bullets
        for bullet in slide.bullets:
            assert "…" not in bullet


def test_no_duplicate_takeaways(analysis: SourceAnalysis) -> None:
    deck = _plan(analysis, _request())
    takeaways = [slide.takeaway for slide in deck.slides]
    assert len(takeaways) == len(set(takeaways))


def test_required_keywords_appear_in_deck(analysis: SourceAnalysis) -> None:
    request = _request()
    deck = _plan(analysis, request)
    text = " ".join(
        " ".join([slide.title, slide.takeaway, *slide.bullets]) for slide in deck.slides
    )
    for keyword in request.keywords:
        assert keyword in text, f"필수 키워드 '{keyword}' 가 덱에 없습니다"


def test_five_minute_deck_is_about_five_slides(analysis: SourceAnalysis) -> None:
    deck = _plan(analysis, _request(duration_minutes=5, slide_count=5))
    assert 4 <= len(deck.slides) <= 6


def test_deck_title_is_not_truncated(analysis: SourceAnalysis) -> None:
    deck = _plan(analysis, _request())
    assert deck.title
    assert "…" not in deck.title
