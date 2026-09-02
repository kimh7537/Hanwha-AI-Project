"""모듈 D: 발표 스크립트와 예상 Q&A (docs/05-presentation-support.md)."""

from __future__ import annotations

import pytest

from app.llm.base import RunContext
from app.models.contracts import PresentationRequest, SourceAnalysis
from app.services.audience import transform
from app.services.planner import plan
from app.services.support import build_support


def _request(audience: str = "customer", **overrides) -> PresentationRequest:
    payload = {
        "audience": audience,
        "purpose": "technical_explanation",
        "duration_minutes": 5,
        "keywords": ["정확도", "도입 효과"],
        "style": "persuasive",
        "preserve_original_terms": True,
    }
    payload.update(overrides)
    return PresentationRequest(**payload)


def _build(analysis: SourceAnalysis, request: PresentationRequest):
    ctx = RunContext()
    content = transform(analysis, request, ctx)
    deck = plan(content, analysis, request, ctx)
    return deck, build_support(deck, content, analysis, request, ctx)


def test_one_script_per_slide(analysis: SourceAnalysis) -> None:
    deck, support = _build(analysis, _request())
    assert [s.slide_id for s in support.scripts] == [slide.id for slide in deck.slides]
    assert all(script.script for script in support.scripts)
    assert all(script.must_say for script in support.scripts)


def test_total_duration_matches_requested_time(analysis: SourceAnalysis) -> None:
    request = _request(duration_minutes=5)
    _deck, support = _build(analysis, request)

    total = sum(script.duration_seconds for script in support.scripts)
    target = request.duration_minutes * 60
    assert 0.8 * target <= total <= 1.2 * target, f"스크립트 합계 {total}초 (목표 {target}초)"


def test_qa_count_is_within_range(analysis: SourceAnalysis) -> None:
    _deck, support = _build(analysis, _request())
    assert 3 <= len(support.qa) <= 5


def test_questions_differ_by_audience(analysis: SourceAnalysis) -> None:
    _d1, newcomer = _build(analysis, _request("newcomer"))
    _d2, executive = _build(analysis, _request("executive"))

    newcomer_questions = {item.question for item in newcomer.qa}
    executive_questions = {item.question for item in executive.qa}
    assert not newcomer_questions & executive_questions

    assert any("비용" in q or "일정" in q for q in executive_questions)


def test_unanswerable_question_is_marked_not_invented(analysis: SourceAnalysis) -> None:
    """원문에 비용 정보가 없다. 답을 지어내지 않고 '원문 확인 필요'로 표시해야 한다."""
    _deck, support = _build(analysis, _request("executive"))
    cost = next(item for item in support.qa if "비용" in item.question)

    assert cost.answer.startswith("원문 확인 필요")
    assert cost.source_refs == []


def test_answers_with_refs_are_grounded(analysis: SourceAnalysis) -> None:
    _deck, support = _build(analysis, _request())
    known = {e.id for e in analysis.source_evidence}

    for item in support.qa:
        if item.source_refs:
            assert set(item.source_refs) <= known
        else:
            assert item.answer.startswith("원문 확인 필요")


def test_rehearsal_cards_point_at_real_slides(analysis: SourceAnalysis) -> None:
    deck, support = _build(analysis, _request())
    slide_ids = {slide.id for slide in deck.slides}

    assert support.rehearsal_cards
    for card in support.rehearsal_cards:
        assert card.recommended_slide in slide_ids


@pytest.mark.parametrize("audience", ["newcomer", "practitioner", "executive", "customer"])
def test_scripts_do_not_repeat_the_same_sentence(
    analysis: SourceAnalysis, audience: str
) -> None:
    _deck, support = _build(analysis, _request(audience))
    for script in support.scripts:
        sentences = [s.strip() for s in script.script.split(". ") if len(s.strip()) > 15]
        assert len(sentences) == len(set(sentences)), f"{script.slide_id} 스크립트에 같은 문장이 반복됩니다"
