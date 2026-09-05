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


def test_audience_changes_the_slide_budget() -> None:
    """같은 5분이라도 청중이 다르면 장수가 달라야 한다.

    여기가 같아지면 청중 조건은 '표현만 바꾸는 옵션'이 된다 (docs/04).
    """

    def count(audience: str) -> int:
        return resolve_slide_count(_request(audience=audience, slide_count=None))

    assert count("executive") < count("customer") < count("newcomer")
    assert count("practitioner") > count("executive")


def test_explicit_slide_count_skips_the_audience_delta() -> None:
    """사용자가 장수를 직접 지정하면 청중 보정을 걸지 않는다."""
    for audience in ("newcomer", "practitioner", "executive", "customer"):
        assert resolve_slide_count(_request(audience=audience, slide_count=6)) == 6


def test_audience_changes_structure_not_just_wording(analysis: SourceAnalysis) -> None:
    """청중을 바꾸면 슬라이드 구성 자체가 달라진다."""
    newcomer = _plan(analysis, _request(audience="newcomer", slide_count=None))
    executive = _plan(analysis, _request(audience="executive", slide_count=None))

    assert len(newcomer.slides) != len(executive.slides)
    assert [s.title for s in newcomer.slides] != [s.title for s in executive.slides]
    # 임원 덱은 결론이 맨 앞이다.
    assert "결론" in executive.slides[0].title


def test_strategy_is_filled_and_audience_specific(analysis: SourceAnalysis) -> None:
    """구성 전략이 비면 '다시 설계했다'는 근거가 화면에서 사라진다."""
    newcomer = _plan(analysis, _request(audience="newcomer", slide_count=None))
    executive = _plan(analysis, _request(audience="executive", slide_count=None))

    assert len(newcomer.strategy) >= 20
    assert newcomer.strategy != executive.strategy
    assert str(len(newcomer.slides)) in newcomer.strategy


def test_conclusion_stays_last(analysis: SourceAnalysis) -> None:
    """보충 슬라이드가 결론 뒤에 붙으면 덱이 이상해진다."""
    for audience in ("newcomer", "practitioner", "customer"):
        deck = _plan(analysis, _request(audience=audience, slide_count=None))
        assert deck.slides[-1].title.startswith("결론")


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


@pytest.mark.parametrize("wanted", [3, 5, 8, 10])
def test_requested_slide_count_is_honored(analysis: SourceAnalysis, wanted: int) -> None:
    """LLM 없이도 사용자가 고른 장수를 그대로 만든다.

    한때 보충 슬라이드가 수치·조건·용어 각 한 장으로 묶여 있어 재료가 남아도 8장에서 멈췄다.
    조건 화면이 고른 장수를 그대로 예고하므로, 모자라면 그 예고가 거짓말이 된다.
    """
    deck = _plan(analysis, _request(duration_minutes=10, slide_count=wanted))
    assert len(deck.slides) == wanted
    # 장수를 채우려고 근거 없는 슬라이드를 만들지 않는다.
    assert all(slide.source_refs for slide in deck.slides)


def test_repeated_extra_slides_are_distinguishable(analysis: SourceAnalysis) -> None:
    """같은 종류가 여러 장이면 제목·결론이 서로 달라야 한 장을 복사한 것으로 보이지 않는다."""
    deck = _plan(analysis, _request(duration_minutes=10, slide_count=10))
    titles = [slide.title for slide in deck.slides]
    takeaways = [slide.takeaway for slide in deck.slides]
    assert len(titles) == len(set(titles))
    assert len(takeaways) == len(set(takeaways))
