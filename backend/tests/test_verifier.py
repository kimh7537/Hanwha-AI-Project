"""모듈 E: 원문 대비 검증 (docs/06-verification.md)."""

from __future__ import annotations

from app.models.contracts import (
    IssueType,
    PresentationRequest,
    PresentationSupport,
    ReportStatus,
    Severity,
    Slide,
    SlideDeck,
    SourceAnalysis,
)
from app.services.verifier import verify

from tests.conftest import load_fixture


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


def _deck() -> SlideDeck:
    return SlideDeck(**load_fixture("slide_deck.json"))


def _support() -> PresentationSupport:
    return PresentationSupport(**load_fixture("presentation_support.json"))


def test_generated_deck_is_explainable(analysis: SourceAnalysis) -> None:
    """데모 성공 기준 6번: 설명 가능한 결과가 나와야 한다."""
    report = verify(_deck(), _support(), analysis, _request())

    assert report.summary
    assert report.status in {ReportStatus.OK, ReportStatus.WARNING, ReportStatus.REVIEW_NEEDED}
    assert report.checked_slides == len(_deck().slides)
    for item in report.items:
        assert item.message
        assert item.suggested_fix


def test_fabricated_number_is_caught(analysis: SourceAnalysis) -> None:
    deck = _deck()
    deck.slides[0].bullets.append("분류 정확도는 99.9% 입니다")

    report = verify(deck, _support(), analysis, _request())

    number_errors = [i for i in report.items if i.type is IssueType.NUMBER_ERROR]
    assert any("99.9" in item.message for item in number_errors)
    assert report.status is ReportStatus.REVIEW_NEEDED


def test_slide_without_evidence_is_caught(analysis: SourceAnalysis) -> None:
    deck = _deck()
    deck.slides.append(
        Slide(id="slide-99", title="추가 제안", takeaway="도입을 권장합니다", bullets=["근거 없음"])
    )

    report = verify(deck, _support(), analysis, _request())

    unsupported = [i for i in report.items if i.type is IssueType.UNSUPPORTED_CLAIM]
    assert any(item.slide_id == "slide-99" for item in unsupported)
    assert report.status is ReportStatus.REVIEW_NEEDED


def test_unknown_chunk_reference_is_caught(analysis: SourceAnalysis) -> None:
    deck = _deck()
    deck.slides[0].source_refs = ["chunk-99"]

    report = verify(deck, _support(), analysis, _request())
    assert any(
        item.type is IssueType.UNSUPPORTED_CLAIM and "chunk-99" in item.message
        for item in report.items
    )


def test_missing_keyword_is_reported(analysis: SourceAnalysis) -> None:
    report = verify(_deck(), _support(), analysis, _request(keywords=["존재하지않는키워드"]))
    assert any(i.type is IssueType.OMISSION for i in report.items)


def test_internal_information_flagged_only_for_customers(analysis: SourceAnalysis) -> None:
    deck = _deck()
    deck.slides[0].bullets.append("사내 K-Drive 연동은 정보보호팀 승인이 필요합니다")

    customer = verify(deck, _support(), analysis, _request("customer"))
    practitioner = verify(deck, _support(), analysis, _request("practitioner"))

    assert any(i.type is IssueType.SENSITIVE_INFO for i in customer.items)
    assert not any(i.type is IssueType.SENSITIVE_INFO for i in practitioner.items)


def test_qualified_number_quoted_without_condition_is_distortion(
    analysis: SourceAnalysis,
) -> None:
    """'정확도 94.2%' 는 원문에서 조건이 붙은 수치다. 조건 없이 인용하면 단정이 된다."""
    deck = SlideDeck(
        title="테스트",
        slides=[
            Slide(
                id="slide-1",
                title="성능",
                takeaway="정확도 94.2% 를 달성했습니다",
                bullets=["정확도 94.2%"],
                source_refs=[analysis.source_evidence[0].id],
            )
        ],
    )

    report = verify(deck, PresentationSupport(), analysis, _request())
    assert any(i.type is IssueType.DISTORTION for i in report.items)


def test_clean_deck_reports_ok(analysis: SourceAnalysis) -> None:
    """모든 조건을 담고 근거가 붙은 덱은 '확인됨' 이 나와야 한다."""
    bullets = [item.text for item in analysis.must_keep]
    deck = SlideDeck(
        title="테스트",
        slides=[
            Slide(
                id="slide-1",
                title="적용 조건",
                takeaway="적용 전 확인이 필요한 조건입니다",
                bullets=bullets,
                source_refs=[e.id for e in analysis.source_evidence],
            )
        ],
    )

    report = verify(deck, PresentationSupport(), analysis, _request("practitioner", keywords=[]))

    assert not [i for i in report.items if i.severity is Severity.CRITICAL]
    assert report.status is ReportStatus.OK
    assert "찾지 못했습니다" in report.summary
