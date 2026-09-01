"""검색 경로 테스트 (docs/02-document-analysis.md).

핵심 계약 두 가지를 고정한다.
  1. 문서가 프롬프트 예산 안에 들어가면 검색을 아예 하지 않는다 (mock 데모는 네트워크를 타지 않는다).
  2. Chroma 가 실패해도 파이프라인은 멈추지 않고 keyword 로 계속한다.
"""

from __future__ import annotations

import pytest

from app.llm.base import MockProvider, RunContext
from app.models.contracts import Chunk
from app.services import retrieval


def make_chunks(texts: list[str]) -> list[Chunk]:
    return [
        Chunk(id=f"chunk-{i + 1:02d}", index=i, page=1, text=text)
        for i, text in enumerate(texts)
    ]


@pytest.fixture()
def long_chunks() -> list[Chunk]:
    """예산을 넘기는 문서. 마지막 chunk 에만 키워드가 들어 있다."""
    filler = ["관련 없는 배경 설명 문장이다." * 20 for _ in range(9)]
    return make_chunks(filler + ["도입 효과는 담당자 확인 시간을 줄이는 것이다." * 20])


class BrokenRetriever(retrieval.Retriever):
    name = "chroma"

    def rank(self, chunks, query, namespace=""):  # type: ignore[no-untyped-def]
        raise retrieval.RetrievalError("연결 실패(테스트)")


def test_small_document_is_passed_through_untouched() -> None:
    """예산 안에 들어가면 순서·개수 모두 그대로여야 한다."""
    chunks = make_chunks(["첫 문단이다.", "둘째 문단이다.", "셋째 문단이다."])
    picked = retrieval.select_chunks(chunks, ["효과"], max_chars=10_000)
    assert [c.id for c in picked] == ["chunk-01", "chunk-02", "chunk-03"]


def test_never_calls_retriever_when_budget_fits() -> None:
    """작은 문서에서는 검색 백엔드를 건드리지 않는다 (네트워크 없이 데모 가능)."""
    chunks = make_chunks(["짧은 문서다."])
    # 호출되면 예외가 나는 retriever 를 넣어도 통과해야 한다
    picked = retrieval.select_chunks(
        chunks, ["효과"], max_chars=10_000, retriever=BrokenRetriever()
    )
    assert picked == chunks


def test_keyword_ranking_rescues_the_last_chunk(long_chunks: list[Chunk]) -> None:
    """앞에서부터 자르면 버려졌을 뒤쪽 chunk 가 키워드 덕분에 선택된다."""
    budget = len(long_chunks[0].text) * 3
    picked = retrieval.select_chunks(long_chunks, ["도입 효과"], max_chars=budget)

    assert "chunk-10" in [c.id for c in picked]
    # 예산을 넘지 않는다
    assert retrieval.fits_budget(picked, budget)
    # 반환 순서는 항상 문서 순서다
    assert [c.index for c in picked] == sorted(c.index for c in picked)


def test_chroma_failure_falls_back_to_keyword(long_chunks: list[Chunk]) -> None:
    """Chroma 가 죽어도 결과가 나오고, 그 사실이 note 로 남는다."""
    ctx = RunContext(provider=MockProvider())
    budget = len(long_chunks[0].text) * 3

    picked = retrieval.select_chunks(
        long_chunks, ["도입 효과"], max_chars=budget, retriever=BrokenRetriever(), ctx=ctx
    )

    assert picked, "fallback 이 빈 결과를 내면 안 된다"
    assert "chunk-10" in [c.id for c in picked]
    assert any("retrieval" in note for note in ctx.notes)
    # 검색 강등은 LLM 실패가 아니므로 fallback_used 를 켜지 않는다
    assert ctx.fallback_used is False


def test_oversized_single_chunk_still_returns_something() -> None:
    """chunk 하나가 예산보다 커도 빈 프롬프트를 만들지 않는다."""
    chunks = make_chunks(["아주 긴 문단이다." * 500])
    picked = retrieval.select_chunks(chunks, ["효과"], max_chars=100)
    assert len(picked) == 1


def test_build_retriever_without_chroma_settings_is_keyword() -> None:
    from app.config import Settings

    settings = Settings(chroma_api_key="", chroma_tenant="", chroma_database="")
    assert retrieval.build_retriever(settings).name == "keyword"


def test_collection_name_is_valid_for_chroma() -> None:
    """Chroma 컬렉션 이름 규칙: 영숫자로 시작·끝, 3~63자."""
    for namespace in ["doc-01f3f54b", "", "한글/문서 이름!!", "x" * 200]:
        name = retrieval._collection_name(namespace)
        assert 3 <= len(name) <= 63
        assert name[0].isalnum() and name[-1].isalnum()
