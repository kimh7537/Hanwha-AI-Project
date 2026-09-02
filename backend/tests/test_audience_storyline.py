"""청중별 이야기 순서가 선언과 실제 결과에서 같은지 대조한다.

조건 화면은 생성을 누르기 전에 `AUDIENCE_STORYLINE` 을 그대로 보여주며 "이 청중이면 이 순서로
짜입니다"라고 예고한다. 선언과 결과가 갈라지면 화면이 하지 않는 일을 말하게 되므로 여기서 막는다.

같은 값이 LLM 프롬프트의 구성 지시로도 나가지만(prompts/audience.py), LLM 응답까지 단정할 수는
없다. 테스트가 보장하는 것은 휴리스틱 경로의 순서와, 양쪽 경로가 같은 상수에서 나온다는 사실이다.
"""

from __future__ import annotations

import pytest

from app.models.contracts import Audience, PresentationRequest, SourceAnalysis
from app.services.audience import (
    AUDIENCE_GLOSSARY_LIMIT,
    AUDIENCE_LEADS,
    AUDIENCE_STORYLINE,
    AUDIENCE_TRIMS,
    transform_heuristic,
)


def _request(audience: Audience) -> PresentationRequest:
    return PresentationRequest(
        audience=audience,
        purpose="technical_explanation",
        duration_minutes=5,
        keywords=[],
        style="professional",
        preserve_original_terms=True,
    )


@pytest.mark.parametrize("audience", list(Audience), ids=lambda a: a.value)
def test_storyline_covers_every_audience(audience: Audience) -> None:
    """네 청중 모두 선언이 있어야 한다. 빠지면 화면의 미리보기가 비어 버린다."""
    assert AUDIENCE_STORYLINE[audience]
    assert AUDIENCE_LEADS[audience]
    assert AUDIENCE_TRIMS[audience]
    assert audience in AUDIENCE_GLOSSARY_LIMIT


@pytest.mark.parametrize("audience", list(Audience), ids=lambda a: a.value)
def test_heuristic_topics_follow_storyline(audience: Audience, analysis: SourceAnalysis) -> None:
    """실제로 만들어지는 설명의 topic 이 선언한 순서를 그대로 따른다.

    근거가 없어 채우지 못한 항목은 건너뛸 수 있으므로 '부분 수열'로 본다 — 순서가 바뀌거나
    선언에 없는 topic 이 나오면 실패다.
    """
    content = transform_heuristic(analysis, _request(audience))
    produced = [e.topic for e in content.explanations]
    declared = AUDIENCE_STORYLINE[audience]

    assert produced, "설명이 하나도 만들어지지 않았습니다"
    assert set(produced) <= set(declared), f"선언에 없는 topic: {set(produced) - set(declared)}"
    assert produced == [topic for topic in declared if topic in produced]


def test_storylines_differ_between_audiences() -> None:
    """청중이 바뀌면 뼈대가 바뀐다 — 이 프로젝트의 주장 자체다.

    문장만 달라지고 구성이 같으면 "프롬프트 옵션을 UI 로 만든 것"과 구분되지 않는다.
    """
    storylines = [tuple(AUDIENCE_STORYLINE[audience]) for audience in Audience]
    assert len(set(storylines)) == len(storylines)

    # 어느 두 청중도 순서를 절반 넘게 공유하지 않는다.
    for index, first in enumerate(storylines):
        for second in storylines[index + 1 :]:
            shared = set(first) & set(second)
            assert len(shared) * 2 <= min(len(first), len(second))


def test_glossary_limit_differs_by_audience(analysis: SourceAnalysis) -> None:
    """용어 풀이 개수는 청중별로 다르다. 임원에게는 넣지 않는다."""
    assert AUDIENCE_GLOSSARY_LIMIT[Audience.EXECUTIVE] == 0
    assert AUDIENCE_GLOSSARY_LIMIT[Audience.NEWCOMER] is None  # 전부

    newcomer = transform_heuristic(analysis, _request(Audience.NEWCOMER))
    executive = transform_heuristic(analysis, _request(Audience.EXECUTIVE))
    assert len(newcomer.glossary) == len(analysis.terms)
    assert executive.glossary == []
