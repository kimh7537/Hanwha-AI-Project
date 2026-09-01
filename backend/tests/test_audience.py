"""모듈 B: 청중 맞춤 변환 (docs/03-audience-transform.md).

이 파일의 핵심은 '사실은 유지하고 표현의 깊이만 바꾼다'를 기계적으로 증명하는 것이다.
데모 성공 기준 7번의 근거이기도 하다.
"""

from __future__ import annotations

import pytest

from app.llm.base import RunContext
from app.models.contracts import Audience, PresentationRequest, SourceAnalysis
from app.services.audience import transform


def _request(audience: str, **overrides) -> PresentationRequest:
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


def _numbers_in(analysis: SourceAnalysis) -> set[str]:
    return {f"{n.value}{n.unit}" for n in analysis.numbers}


def test_newcomer_and_executive_differ(analysis: SourceAnalysis) -> None:
    newcomer = transform(analysis, _request("newcomer"), RunContext())
    executive = transform(analysis, _request("executive"), RunContext())

    # 신입에게는 용어를 풀어 주고, 임원에게는 용어 풀이를 하지 않는다
    assert len(newcomer.glossary) > len(executive.glossary)

    newcomer_topics = {e.topic for e in newcomer.explanations}
    executive_topics = {e.topic for e in executive.explanations}
    assert newcomer_topics != executive_topics

    assert newcomer.emphasis != executive.emphasis


def test_facts_are_identical_across_audiences(analysis: SourceAnalysis) -> None:
    """청중이 달라도 사실(수치)은 같아야 한다. 표현의 깊이만 바뀐다."""
    before = _numbers_in(analysis)
    for audience in ("newcomer", "practitioner", "executive", "customer"):
        transform(analysis, _request(audience), RunContext())
        assert _numbers_in(analysis) == before


@pytest.mark.parametrize(
    "audience", ["newcomer", "practitioner", "executive", "customer"]
)
def test_explanations_keep_source_refs(analysis: SourceAnalysis, audience: str) -> None:
    content = transform(analysis, _request(audience), RunContext())
    known = {e.id for e in analysis.source_evidence}

    assert content.explanations
    for explanation in content.explanations:
        assert explanation.source_refs
        assert set(explanation.source_refs) <= known


def test_practitioner_keeps_all_conditions(analysis: SourceAnalysis) -> None:
    content = transform(analysis, _request("practitioner"), RunContext())
    body = " ".join(e.text for e in content.explanations)
    assert "마스킹" in body


def test_customer_gets_internal_information_warning(analysis: SourceAnalysis) -> None:
    content = transform(analysis, _request("customer"), RunContext())
    assert content.audience is Audience.CUSTOMER
    assert content.cautions
    assert any("검토" in caution for caution in content.cautions)


def test_non_customer_has_no_public_review_warning(analysis: SourceAnalysis) -> None:
    content = transform(analysis, _request("practitioner"), RunContext())
    assert not any("고객 공개" in caution for caution in content.cautions)


def test_original_terms_can_be_dropped(analysis: SourceAnalysis) -> None:
    kept = transform(analysis, _request("newcomer", preserve_original_terms=True), RunContext())
    dropped = transform(
        analysis, _request("newcomer", preserve_original_terms=False), RunContext()
    )

    kept_terms = " ".join(g.term for g in kept.glossary)
    dropped_terms = " ".join(g.term for g in dropped.glossary)
    assert "embedding" in kept_terms
    assert "embedding" not in dropped_terms
