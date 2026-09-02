"""원어 유지 옵션이 화면 전체에서 일관되게 적용되는지 (docs/03-audience-transform.md).

용어 풀이에는 '임베딩', 예상 질문에는 '임베딩(embedding)' 처럼 어긋나면 안 된다.
"""

from __future__ import annotations

import pytest

from app.llm.base import RunContext
from app.models.contracts import PresentationRequest, SourceAnalysis
from app.services.audience import transform
from app.services.planner import plan
from app.services.support import build_support


def _request(preserve: bool) -> PresentationRequest:
    return PresentationRequest(
        audience="newcomer",
        purpose="education",
        duration_minutes=5,
        keywords=[],
        style="friendly",
        preserve_original_terms=preserve,
        slide_count=5,
    )


def _run(analysis: SourceAnalysis, preserve: bool):
    request = _request(preserve)
    ctx = RunContext()
    content = transform(analysis, request, ctx)
    deck = plan(content, analysis, request, ctx)
    return content, build_support(deck, content, analysis, request, ctx)


@pytest.mark.parametrize("preserve", [True, False])
def test_glossary_and_questions_agree(analysis: SourceAnalysis, preserve: bool) -> None:
    content, support = _run(analysis, preserve)
    questions = " ".join(item.question for item in support.qa)

    assert content.glossary, "신입사원에게는 용어 풀이가 있어야 한다"
    has_english_in_glossary = any("(" in item.term and item.term[-2].isascii() for item in content.glossary)
    has_english_in_questions = "(embedding)" in questions or "(ensemble)" in questions

    if preserve:
        assert has_english_in_glossary
        assert has_english_in_questions
    else:
        assert not has_english_in_glossary
        assert not has_english_in_questions
