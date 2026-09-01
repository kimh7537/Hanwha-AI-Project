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


# --- Chroma Cloud 호출 경로 -------------------------------------------------
#
# 실제 Chroma 를 부르지 않고, 클라이언트가 지켜야 할 계약만 가짜 클라이언트로 고정한다.
# 이 경로는 CHROMA_* 가 채워진 환경에서만 도는데, 테스트는 항상 그 반대다(conftest).


class FakeCollection:
    def __init__(self, name: str, ranked: list[str], stored: int = 0) -> None:
        self.name = name
        self._ranked = ranked
        self._count = stored
        self.upserts: list[list[str]] = []
        self.query_kwargs: dict = {}
        self.raise_on_query: Exception | None = None

    def count(self) -> int:
        return self._count

    def upsert(self, ids, documents, metadatas):  # type: ignore[no-untyped-def]
        assert len(ids) == len(documents) == len(metadatas)
        self.upserts.append(list(ids))
        self._count += len(ids)

    def query(self, **kwargs):  # type: ignore[no-untyped-def]
        self.query_kwargs = kwargs
        if self.raise_on_query is not None:
            raise self.raise_on_query
        return {"ids": [list(self._ranked)]}


class FakeClient:
    def __init__(self, ranked: list[str], stored: int = 0, max_batch: int | None = 5461) -> None:
        self.collection = FakeCollection("", ranked, stored)
        self._max_batch = max_batch
        self.created: list[str] = []

    def get_or_create_collection(self, name: str) -> FakeCollection:
        self.created.append(name)
        self.collection.name = name
        return self.collection

    def get_max_batch_size(self) -> int:
        if self._max_batch is None:
            raise RuntimeError("상한을 알려주지 않는 서버(테스트)")
        return self._max_batch


def make_chroma(client: FakeClient) -> retrieval.ChromaRetriever:
    from app.config import Settings

    settings = Settings(chroma_api_key="k", chroma_tenant="t", chroma_database="d")
    return retrieval.ChromaRetriever(settings, client=client)


def test_chroma_returns_server_ranking_first() -> None:
    """Chroma 가 매긴 순위가 그대로 반영되어야 한다."""
    chunks = make_chunks(["첫", "둘", "셋"])
    retriever = make_chroma(FakeClient(ranked=["chunk-03", "chunk-01", "chunk-02"]))

    assert retriever.rank(chunks, "도입 효과", "doc-1") == ["chunk-03", "chunk-01", "chunk-02"]


def test_chroma_appends_missing_chunks_in_document_order() -> None:
    """서버가 일부만 돌려줘도 나머지는 문서 순서로 이어 붙는다 (누락 금지)."""
    chunks = make_chunks(["첫", "둘", "셋", "넷"])
    retriever = make_chroma(FakeClient(ranked=["chunk-03"]))

    assert retriever.rank(chunks, "효과", "doc-1") == [
        "chunk-03",
        "chunk-01",
        "chunk-02",
        "chunk-04",
    ]


def test_chroma_ignores_ids_that_are_not_in_this_document() -> None:
    """옛 색인이 남아 있어도 이 문서의 chunk 만 쓴다."""
    chunks = make_chunks(["첫", "둘"])
    retriever = make_chroma(FakeClient(ranked=["chunk-99", "chunk-02", "chunk-01"]))

    assert retriever.rank(chunks, "효과", "doc-1") == ["chunk-02", "chunk-01"]


def test_chroma_requests_ids_only() -> None:
    """id 만 있으면 되므로 documents·distances 를 돌려받지 않는다 (응답·요금 절약)."""
    chunks = make_chunks(["첫", "둘"])
    client = FakeClient(ranked=["chunk-01", "chunk-02"])
    make_chroma(client).rank(chunks, "효과", "doc-1")

    assert client.collection.query_kwargs["include"] == []
    assert client.collection.query_kwargs["n_results"] == 2


def test_chroma_caps_n_results() -> None:
    """n_results 는 상한을 넘지 않는다. 프롬프트 예산은 그보다 훨씬 먼저 찬다."""
    many = make_chunks([f"문단 {i}" for i in range(retrieval.MAX_QUERY_RESULTS + 50)])
    client = FakeClient(ranked=[c.id for c in many])
    make_chroma(client).rank(many, "효과", "doc-1")

    assert client.collection.query_kwargs["n_results"] == retrieval.MAX_QUERY_RESULTS


def test_chroma_upserts_in_batches() -> None:
    """서버 상한보다 큰 문서는 나눠 보낸다. 한 번에 보내면 요청이 거부된다."""
    chunks = make_chunks([f"문단 {i}" for i in range(5)])
    client = FakeClient(ranked=[c.id for c in chunks], max_batch=2)
    make_chroma(client).rank(chunks, "효과", "doc-1")

    assert [len(batch) for batch in client.collection.upserts] == [2, 2, 1]
    # 나눠 보내도 모든 chunk 가 한 번씩 올라간다
    sent = [chunk_id for batch in client.collection.upserts for chunk_id in batch]
    assert sent == [c.id for c in chunks]


def test_chroma_batch_size_falls_back_when_server_is_silent() -> None:
    """상한을 못 물어봐도 색인은 계속된다."""
    chunks = make_chunks([f"문단 {i}" for i in range(3)])
    client = FakeClient(ranked=[c.id for c in chunks], max_batch=None)
    make_chroma(client).rank(chunks, "효과", "doc-1")

    assert len(client.collection.upserts) == 1


def test_chroma_skips_reindex_when_collection_already_matches() -> None:
    """같은 문서로 청중만 바꿔 재생성할 때 임베딩·쓰기를 다시 치르지 않는다."""
    chunks = make_chunks(["첫", "둘", "셋"])
    client = FakeClient(ranked=[c.id for c in chunks], stored=3)
    make_chroma(client).rank(chunks, "효과", "doc-1")

    assert client.collection.upserts == []


def test_chroma_indexes_when_collection_is_stale() -> None:
    """개수가 다르면 다시 색인한다."""
    chunks = make_chunks(["첫", "둘", "셋"])
    client = FakeClient(ranked=[c.id for c in chunks], stored=1)
    make_chroma(client).rank(chunks, "효과", "doc-1")

    assert client.collection.upserts == [["chunk-01", "chunk-02", "chunk-03"]]


def test_chroma_uses_namespace_as_collection_name() -> None:
    """컬렉션은 문서마다 하나다."""
    chunks = make_chunks(["첫"])
    client = FakeClient(ranked=["chunk-01"])
    make_chroma(client).rank(chunks, "효과", "doc-01f3f54b")

    assert client.created == ["audiencedeck-doc-01f3f54b"]


def test_chroma_empty_query_never_touches_the_network() -> None:
    """질의가 없으면 임베딩 검색으로 얻을 것이 없다. 호출도 하지 않는다."""
    chunks = make_chunks(["첫", "둘"])
    client = FakeClient(ranked=[])
    picked = make_chroma(client).rank(chunks, "   ", "doc-1")

    assert picked == ["chunk-01", "chunk-02"]
    assert client.created == []


def test_chroma_empty_result_raises_retrieval_error() -> None:
    """빈 순위를 받으면 조용히 넘기지 않고 keyword 로 되돌릴 수 있게 던진다."""
    chunks = make_chunks(["첫", "둘"])
    with pytest.raises(retrieval.RetrievalError):
        make_chroma(FakeClient(ranked=[])).rank(chunks, "효과", "doc-1")


def test_chroma_query_failure_becomes_retrieval_error() -> None:
    """서버 예외가 파이프라인까지 올라가면 안 된다."""
    chunks = make_chunks(["첫", "둘"])
    client = FakeClient(ranked=["chunk-01"])
    client.collection.raise_on_query = RuntimeError("429 Too Many Requests")

    with pytest.raises(retrieval.RetrievalError):
        make_chroma(client).rank(chunks, "효과", "doc-1")


def test_chroma_failure_is_recoverable_end_to_end(long_chunks: list[Chunk]) -> None:
    """실패한 Chroma retriever 를 select_chunks 에 넣어도 결과가 나온다."""
    client = FakeClient(ranked=["chunk-01"])
    client.collection.raise_on_query = RuntimeError("연결 끊김(테스트)")
    ctx = RunContext(provider=MockProvider())
    budget = len(long_chunks[0].text) * 3

    picked = retrieval.select_chunks(
        long_chunks, ["도입 효과"], max_chars=budget, retriever=make_chroma(client), ctx=ctx
    )

    assert picked
    assert any("retrieval" in note for note in ctx.notes)
    assert ctx.fallback_used is False


def test_build_retriever_records_connection_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """자격증명이 틀려 keyword 로 내려간 사실이 note 로 남아야 한다."""
    from app.config import Settings

    def boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise retrieval.RetrievalError("인증 실패(테스트)")

    monkeypatch.setattr(retrieval, "ChromaRetriever", boom)
    ctx = RunContext(provider=MockProvider())
    settings = Settings(chroma_api_key="k", chroma_tenant="t", chroma_database="d")

    assert retrieval.build_retriever(settings, ctx=ctx).name == "keyword"
    assert any("인증 실패" in note for note in ctx.notes)


def test_build_cloud_client_requires_all_three_settings() -> None:
    from app.config import Settings

    settings = Settings(chroma_api_key="k", chroma_tenant="", chroma_database="d")
    with pytest.raises(retrieval.RetrievalError):
        retrieval.build_cloud_client(settings)
