"""모듈 A: SourceAnalysis 추출 (docs/02-document-analysis.md)."""

from __future__ import annotations

from app.llm.base import RunContext
from app.models.contracts import Chunk, PresentationRequest
from app.services import textutil
from app.services.analyzer import analyze


def test_every_fact_has_a_valid_source_ref(
    chunks: list[Chunk], customer_request: PresentationRequest
) -> None:
    """근거 추적이 이 프로젝트의 핵심 주장이다."""
    result = analyze(chunks, customer_request, RunContext())
    known = {chunk.id for chunk in chunks}

    groups = (
        result.technical_points,
        result.key_features,
        result.must_keep,
        result.numbers,
        result.terms,
    )
    for group in groups:
        for item in group:
            assert item.source_refs, f"근거 없는 항목이 남아 있습니다: {item}"
            assert set(item.source_refs) <= known


def test_numbers_come_from_the_document(
    chunks: list[Chunk], customer_request: PresentationRequest
) -> None:
    result = analyze(chunks, customer_request, RunContext())
    source = "\n".join(chunk.text for chunk in chunks)

    values = {textutil.number_key(number.value) for number in result.numbers}
    assert "94.2" in values
    assert "12,400" in {number.value for number in result.numbers}

    for number in result.numbers:
        assert number.value in source, f"원문에 없는 값이 추출되었습니다: {number.value}"


def test_versions_and_dates_are_not_treated_as_numbers(
    chunks: list[Chunk], customer_request: PresentationRequest
) -> None:
    """'v2.1', '2026년', 'F1' 은 발표에서 인용할 수치가 아니다."""
    result = analyze(chunks, customer_request, RunContext())
    values = {number.value for number in result.numbers}

    assert "2.1" not in values
    assert "1.0" not in values
    assert "2026" not in values
    # "F1 점수" 의 1 이 수치로 잡히면 안 된다
    assert not any(number.value == "1" for number in result.numbers)


def test_terms_are_real_glossary_entries(
    chunks: list[Chunk], customer_request: PresentationRequest
) -> None:
    result = analyze(chunks, customer_request, RunContext())
    terms = {term.term for term in result.terms}

    assert any("임베딩" in term for term in terms)
    assert any("앙상블" in term for term in terms)
    # 문장을 잘못 자른 조각이 용어로 들어오면 안 된다
    for term in terms:
        assert not term.endswith(("없", "않", "되", "하", "있"))


def test_conditions_are_captured_and_ranked(
    chunks: list[Chunk], customer_request: PresentationRequest
) -> None:
    """검증 모듈이 '과도한 단순화'를 잡으려면 조건 문장이 먼저 수집되어야 한다."""
    result = analyze(chunks, customer_request, RunContext())
    texts = [item.text for item in result.must_keep]

    assert any("마스킹" in text for text in texts)
    assert any("3만 건" in text for text in texts)
    # 강한 조건(금지/전제)이 약한 조건(단순 비교)보다 앞에 온다
    assert textutil.condition_strength(texts[0]) >= textutil.condition_strength(texts[-1])


def test_core_message_is_a_complete_sentence(
    chunks: list[Chunk], customer_request: PresentationRequest
) -> None:
    result = analyze(chunks, customer_request, RunContext())
    assert result.core_message
    assert "…" not in result.core_message
    assert len(result.core_message) > 20


def test_empty_chunks_return_unverified(customer_request: PresentationRequest) -> None:
    result = analyze([], customer_request, RunContext())
    assert result.unverified
