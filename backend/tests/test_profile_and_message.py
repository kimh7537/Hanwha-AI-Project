"""청중 프로파일과 메시지 통제 (docs/01-contracts.md).

이 파일이 지키는 선은 하나다 — **두 기능 모두 사실을 만들거나 지우지 않는다.** 순위를 바꾸고
분량을 정할 뿐이고, 지켜지지 않은 것은 검증 리포트가 잡는다. 순위 조정이 사실 삭제로 새면
원문 대비 검증이라는 이 프로젝트의 나머지 절반이 무너진다.
"""

from __future__ import annotations

import pytest

from app.models.contracts import (
    Audience,
    Interest,
    PresentationRequest,
    SourceAnalysis,
)
from app.services import profile, verifier
from app.services.audience import AUDIENCE_GLOSSARY_LIMIT, resolved_glossary_limit
from app.services.audience import transform_heuristic
from app.services.planner import build_strategy, plan_heuristic
from app.services.support import support_heuristic


def _request(**overrides) -> PresentationRequest:
    payload = {
        "audience": "practitioner",
        "purpose": "technical_explanation",
        "duration_minutes": 5,
        "keywords": [],
        "style": "professional",
        "preserve_original_terms": True,
    }
    payload.update(overrides)
    return PresentationRequest(**payload)


# --------------------------------------------------------------------------
# 기술 이해도
# --------------------------------------------------------------------------


def test_expertise_moves_glossary_within_audience() -> None:
    """이해도는 청중이 정한 기본값을 움직인다. 3 이면 그대로다."""
    base = AUDIENCE_GLOSSARY_LIMIT[Audience.PRACTITIONER]  # 2
    assert profile.resolve_glossary_limit(base, 3) == base
    assert profile.resolve_glossary_limit(base, 1) > base
    assert profile.resolve_glossary_limit(base, 5) < base


def test_low_expertise_gives_executive_glossary() -> None:
    """임원 기본은 0 이지만 이해도가 낮으면 용어를 풀어 준다.

    프로파일은 청중을 덮어쓰는 게 아니라 한 단계 더 좁히는 것이다 — 기술을 모르는 임원에게
    용어 풀이를 주지 않는 것은 청중 규칙을 지킨 게 아니라 발표를 실패시키는 것이다.
    """
    assert AUDIENCE_GLOSSARY_LIMIT[Audience.EXECUTIVE] == 0
    assert resolved_glossary_limit(_request(audience="executive", profile={"expertise": 1})) > 0
    assert resolved_glossary_limit(_request(audience="executive", profile={"expertise": 3})) == 0


def test_high_expertise_trims_newcomer_glossary(analysis: SourceAnalysis) -> None:
    """반대로 이해도가 높으면 신입에게도 용어 풀이가 줄어든다."""
    plain = transform_heuristic(analysis, _request(audience="newcomer", profile={"expertise": 3}))
    expert = transform_heuristic(analysis, _request(audience="newcomer", profile={"expertise": 5}))
    assert len(expert.glossary) < len(plain.glossary)


# --------------------------------------------------------------------------
# 관심 영역
# --------------------------------------------------------------------------


def test_interest_moves_matching_text_forward() -> None:
    """관심 영역에 걸리는 문장이 앞으로 온다. 문장 자체는 그대로다."""
    texts = ["도입 일정은 3개월이 걸린다", "처리 속도가 40% 빨라진다"]
    ranked = profile.rank(texts, _request(profile={"interests": ["performance"]}))
    assert ranked[0] == "처리 속도가 40% 빨라진다"
    assert set(ranked) == set(texts), "순위만 바꾸고 문장을 버리지 않는다"


def test_interest_keeps_every_audience_storyline(analysis: SourceAnalysis) -> None:
    """관심 영역은 뼈대를 바꾸지 않는다 — 뼈대는 청중이 정한다."""
    plain = transform_heuristic(analysis, _request())
    focused = transform_heuristic(
        analysis, _request(profile={"interests": ["cost", "safety"]})
    )
    assert [e.topic for e in plain.explanations] == [e.topic for e in focused.explanations]


# --------------------------------------------------------------------------
# 메시지 통제
# --------------------------------------------------------------------------


def test_minimize_demotes_but_does_not_delete() -> None:
    texts = ["복잡한 기술적 세부사항을 설명한다", "운용 효율이 좋아진다"]
    ranked = profile.rank(texts, _request(message={"minimize": ["복잡한 기술적 세부사항"]}))
    assert ranked[0] == "운용 효율이 좋아진다"
    assert set(ranked) == set(texts), "최소화는 감점이지 삭제가 아니다"


def test_banned_expression_is_demoted_hardest() -> None:
    texts = ["세계 최고 수준의 정확도를 보인다", "정확도는 92% 로 측정됐다"]
    ranked = profile.rank(texts, _request(message={"banned": ["세계 최고"]}))
    assert ranked[0] == "정확도는 92% 로 측정됐다"


def test_must_convey_pulls_matching_sentences_up() -> None:
    texts = ["카테고리는 24종이다", "운용 효율이 기존 대비 좋아진다"]
    ranked = profile.rank(
        texts, _request(message={"must_convey": "기존 대비 운용 효율 향상"})
    )
    assert ranked[0] == "운용 효율이 기존 대비 좋아진다"


def test_verifier_flags_banned_expression_that_survived(
    analysis: SourceAnalysis,
) -> None:
    """고르는 단계에서 피해도 남을 수 있다. 남으면 화면에 띄운다."""
    request = _request(message={"banned": ["분류"]})
    content = transform_heuristic(analysis, request)
    deck = plan_heuristic(content, analysis, request)
    support = support_heuristic(deck, content, analysis, request)

    report = verifier.verify(deck, support, analysis, request)
    banned_items = [item for item in report.items if "사용 금지" in item.message]
    assert banned_items, "금지 표현이 남았는데 리포트가 조용하면 통제 기능이 무의미하다"
    assert all(item.slide_id for item in banned_items), "어느 슬라이드인지 짚어 줘야 고칠 수 있다"


def test_verifier_flags_unconveyed_message(analysis: SourceAnalysis) -> None:
    """반드시 전달하라고 한 메시지가 덱에 없으면 알려 준다. 지어내 넣지 않는다."""
    request = _request(message={"must_convey": "블록체인 마이그레이션 완료"})
    content = transform_heuristic(analysis, request)
    deck = plan_heuristic(content, analysis, request)
    support = support_heuristic(deck, content, analysis, request)

    report = verifier.verify(deck, support, analysis, request)
    assert any("반드시 전달할 메시지" in item.message for item in report.items)

    deck_text = " ".join(
        f"{s.title} {s.takeaway} {' '.join(s.bullets)}" for s in deck.slides
    )
    assert "블록체인" not in deck_text, "근거 없는 메시지를 덱에 넣으면 안 된다"


# --------------------------------------------------------------------------
# 화면에 남는 근거
# --------------------------------------------------------------------------


def test_strategy_records_what_the_profile_did() -> None:
    """"내가 준 조건이 반영됐나"를 확인할 자리가 구성 전략이다."""
    request = _request(
        profile={"expertise": 1, "interests": ["cost"]},
        message={"banned": ["세계 최고"]},
    )
    strategy = build_strategy(request, 5)
    assert "이해도" in strategy
    assert "비용" in strategy
    assert "세계 최고" in strategy


def test_defaults_change_nothing() -> None:
    """프로파일·메시지를 건드리지 않은 요청은 예전과 같은 구성이어야 한다."""
    assert profile.describe(_request()) == []
    assert profile.rank(["가", "나"], _request()) == ["가", "나"]
    for audience in Audience:
        assert resolved_glossary_limit(_request(audience=audience.value)) == (
            AUDIENCE_GLOSSARY_LIMIT[audience]
        )


@pytest.mark.parametrize("interest", list(Interest), ids=lambda i: i.value)
def test_every_interest_has_keywords_and_label(interest: Interest) -> None:
    from app.services.labels import INTEREST_LABELS

    assert profile.INTEREST_KEYWORDS[interest]
    assert INTEREST_LABELS[interest]
