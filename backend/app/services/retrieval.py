"""Retrieval — 프롬프트에 넣을 chunk 를 고른다 (docs/02-document-analysis.md).

원문 전체를 프롬프트에 넣지 않는다. 문서가 예산(`max_prompt_chars`)보다 크면
**문서 앞부분부터 잘라 버리는 대신** 질의와 가까운 chunk 를 고른다.
앞부분부터 자르면 뒤쪽 chunk 는 LLM 에 아예 전달되지 않아 근거가 될 기회조차 없다.

Chroma Cloud 가 설정된 경우에만 임베딩 검색을 쓰고, 없거나 실패하면 keyword 로 되돌아간다.
Chroma 연결 실패가 파이프라인을 멈춰서는 안 된다.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from app.config import Settings, get_settings
from app.llm.base import RunContext
from app.models.contracts import Chunk
from app.services import textutil

# 프롬프트에서 chunk 앞에 붙는 머리말("[chunk-01 | 페이지 3]\n")의 넉넉한 상한
BLOCK_OVERHEAD_CHARS = 32

# Chroma 컬렉션 이름 규칙: 영숫자로 시작·끝, 3~63자, [a-zA-Z0-9._-]
_COLLECTION_SAFE = re.compile(r"[^a-zA-Z0-9._-]")

# 컬렉션 이름 앞머리. 정리 스크립트가 이 접두사로 우리 컬렉션만 골라낸다.
COLLECTION_PREFIX = "audiencedeck-"

# 임베딩 검색 자체의 지연이 데모를 막지 않도록 한 문서당 상한을 둔다.
MAX_INDEXED_CHUNKS = 500

# 프롬프트 예산(기본 12000자)은 chunk 수십 개면 채워진다. 순위 전체를 돌려받을 이유가 없고,
# n_results 를 키우면 응답만 커진다. 여기서 잘린 뒤쪽은 문서 순서로 이어 붙인다.
MAX_QUERY_RESULTS = 200

# 서버가 상한을 알려주지 않을 때 쓰는 보수적인 upsert 배치 크기.
DEFAULT_UPSERT_BATCH = 100


class RetrievalError(RuntimeError):
    """검색 백엔드를 쓸 수 없을 때. 호출자는 반드시 keyword 로 되돌아간다."""


class Retriever:
    """chunk 를 질의 관련도 순으로 정렬한다. 기본 구현은 keyword 방식."""

    name = "keyword"

    def rank(self, chunks: list[Chunk], query: str, namespace: str = "") -> list[str]:
        """관련도가 높은 순서로 chunk id 를 돌려준다."""
        terms = _query_terms(query)
        if not terms:
            return [chunk.id for chunk in chunks]

        scored = [
            (textutil.keyword_overlap(chunk.text, terms), -chunk.index, chunk.id)
            for chunk in chunks
        ]
        scored.sort(reverse=True)
        return [chunk_id for _, _, chunk_id in scored]


class KeywordRetriever(Retriever):
    """기본 경로. 외부 의존성이 없고 항상 동작한다."""


@lru_cache(maxsize=4)
def _cloud_client(api_key: str, tenant: str, database: str) -> Any:
    """자격증명별로 클라이언트를 하나만 만든다.

    `chromadb.CloudClient` 생성자는 tenant/database 를 확인하려고 네트워크를 탄다.
    `/api/health` 와 매 생성 요청이 각각 새로 만들면 그 왕복이 그대로 쌓인다.
    lru_cache 는 예외를 캐시하지 않으므로, 연결에 실패한 자격증명은 다음에 다시 시도된다.
    """
    try:
        import chromadb
    except ImportError as exc:  # pragma: no cover - 설치 환경 문제
        raise RetrievalError(
            "chromadb 패키지가 설치되어 있지 않습니다. requirements.txt 를 설치하세요."
        ) from exc

    try:
        return chromadb.CloudClient(tenant=tenant, database=database, api_key=api_key)
    except Exception as exc:  # noqa: BLE001 - 어떤 실패든 데모를 멈추면 안 된다
        raise RetrievalError(f"Chroma Cloud 에 연결하지 못했습니다: {exc}") from exc


def build_cloud_client(settings: Settings) -> Any:
    """설정에서 Chroma Cloud 클라이언트를 얻는다. 정리 스크립트도 이 경로를 쓴다."""
    if not settings.chroma_enabled:
        raise RetrievalError(
            "CHROMA_API_KEY / CHROMA_TENANT / CHROMA_DATABASE 가 모두 있어야 합니다."
        )
    return _cloud_client(settings.chroma_api_key, settings.chroma_tenant, settings.chroma_database)


class ChromaRetriever(Retriever):
    """Chroma Cloud 임베딩 검색.

    실패하면 `RetrievalError` 를 던진다. 되돌리기는 `select_chunks` 가 담당한다.
    """

    name = "chroma"

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        # client 주입은 테스트용 이음매다. 실제 경로에서는 항상 캐시된 CloudClient 를 쓴다.
        self._client = client if client is not None else build_cloud_client(settings)

    def rank(self, chunks: list[Chunk], query: str, namespace: str = "") -> list[str]:
        if not query.strip():
            # 질의가 없으면 임베딩 검색으로 얻을 것이 없다. 문서 순서가 최선이다.
            return [chunk.id for chunk in chunks]

        indexed = chunks[:MAX_INDEXED_CHUNKS]
        try:
            collection = self._client.get_or_create_collection(name=_collection_name(namespace))
            self._sync(collection, indexed)
            result = collection.query(
                query_texts=[query],
                n_results=min(len(indexed), MAX_QUERY_RESULTS),
                # 우리는 id 만 쓴다. 기본값은 documents·metadatas·distances 까지 돌려주는데,
                # 그만큼 응답이 커지고 Chroma Cloud 는 반환 데이터에 요금을 매긴다.
                include=[],
            )
        except Exception as exc:  # noqa: BLE001
            raise RetrievalError(f"Chroma 검색에 실패했습니다: {exc}") from exc

        ranked = _first_row(result)
        known = {chunk.id for chunk in chunks}
        ordered = [chunk_id for chunk_id in ranked if chunk_id in known]

        if not ordered:
            raise RetrievalError("Chroma 가 chunk 를 하나도 돌려주지 않았습니다.")

        # 색인 상한이나 응답 누락으로 빠진 chunk 는 문서 순서로 뒤에 붙인다.
        seen = set(ordered)
        ordered.extend(chunk.id for chunk in chunks if chunk.id not in seen)
        return ordered

    def _sync(self, collection: Any, indexed: list[Chunk]) -> None:
        """컬렉션을 chunk 와 맞춘다. 이미 같은 개수면 다시 색인하지 않는다.

        컬렉션 이름은 `document_id` 로 고정되고 chunk 는 업로드 시점에 확정된다.
        같은 문서로 청중·시간만 바꿔 다시 생성하는 것이 데모의 기본 동선이라,
        개수가 맞으면 임베딩 계산과 쓰기 요금을 다시 치를 이유가 없다.
        """
        if collection.count() == len(indexed):
            return

        batch = self._batch_size()
        for start in range(0, len(indexed), batch):
            part = indexed[start : start + batch]
            collection.upsert(
                ids=[chunk.id for chunk in part],
                documents=[chunk.text for chunk in part],
                metadatas=[{"page": chunk.page, "index": chunk.index} for chunk in part],
            )

    def _batch_size(self) -> int:
        """서버가 허용하는 최대 배치. 한 번에 다 보내면 큰 문서에서 요청이 거부된다."""
        try:
            reported = int(self._client.get_max_batch_size())
        except Exception:  # noqa: BLE001 - 상한을 못 물어보면 보수적으로 간다
            return DEFAULT_UPSERT_BATCH
        return max(1, min(reported, MAX_INDEXED_CHUNKS))


def _first_row(result: object) -> list[str]:
    """Chroma query 응답에서 id 목록을 꺼낸다. 형태가 다르면 빈 목록."""
    if not isinstance(result, dict):
        return []
    rows = result.get("ids") or []
    if not rows or not isinstance(rows, list):
        return []
    first = rows[0]
    if not isinstance(first, list):
        return []
    return [str(item) for item in first]


def _collection_name(namespace: str) -> str:
    base = _COLLECTION_SAFE.sub("-", namespace or "shared")
    name = f"{COLLECTION_PREFIX}{base}"[:63]
    return name if name[-1].isalnum() else name + "0"


def _query_terms(query: str) -> list[str]:
    return [term for term in re.split(r"[\s,]+", query.strip()) if term]


def build_retriever(settings: Settings | None = None, ctx: RunContext | None = None) -> Retriever:
    """설정에 맞는 retriever 를 만든다. 어떤 실패든 keyword 로 떨어진다."""
    settings = settings or get_settings()
    if not settings.chroma_enabled:
        return KeywordRetriever()
    try:
        return ChromaRetriever(settings)
    except RetrievalError as exc:
        # 자격증명이 틀렸을 때 조용히 keyword 로 내려가면 왜 검색이 안 도는지 알 수 없다.
        if ctx is not None:
            ctx.notes.append(f"retrieval: {exc}")
        return KeywordRetriever()


def fits_budget(chunks: list[Chunk], max_chars: int) -> bool:
    total = sum(len(chunk.text) + BLOCK_OVERHEAD_CHARS for chunk in chunks)
    return total <= max_chars


def select_chunks(
    chunks: list[Chunk],
    keywords: list[str],
    max_chars: int,
    namespace: str = "",
    retriever: Retriever | None = None,
    ctx: RunContext | None = None,
) -> list[Chunk]:
    """예산 안에 들어가는 chunk 를 고른다. 반환 순서는 항상 문서 순서다.

    문서가 예산 안에 들어가면 검색을 아예 하지 않는다 — 작은 문서에서 굳이
    네트워크를 타지 않기 위해서다(docs/02: MVP 는 keyword 로 충분하다).
    """
    if not chunks or fits_budget(chunks, max_chars):
        return chunks

    query = " ".join(term for term in keywords if term).strip()
    retriever = retriever or build_retriever(ctx=ctx)

    try:
        ranked = retriever.rank(chunks, query, namespace)
    except RetrievalError as exc:
        if ctx is not None:
            # fallback_used 는 건드리지 않는다. LLM 실패가 아니라 검색 경로의 강등이며,
            # 화면의 "AI 응답 실패" 배지와 뜻이 다르다.
            ctx.notes.append(f"retrieval: {exc}")
        ranked = KeywordRetriever().rank(chunks, query, namespace)

    by_id = {chunk.id: chunk for chunk in chunks}
    picked: list[Chunk] = []
    used = 0
    for chunk_id in ranked:
        chunk = by_id.get(chunk_id)
        if chunk is None:
            continue
        cost = len(chunk.text) + BLOCK_OVERHEAD_CHARS
        if used + cost > max_chars:
            continue
        picked.append(chunk)
        used += cost

    if not picked:
        # 예산보다 큰 chunk 하나뿐인 경우에도 빈 프롬프트를 만들지 않는다.
        picked = [chunks[0]]

    picked.sort(key=lambda c: c.index)
    return picked
