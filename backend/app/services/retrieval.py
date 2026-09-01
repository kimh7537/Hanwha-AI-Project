"""Retrieval — 프롬프트에 넣을 chunk 를 고른다 (docs/02-document-analysis.md).

원문 전체를 프롬프트에 넣지 않는다. 문서가 예산(`max_prompt_chars`)보다 크면
**문서 앞부분부터 잘라 버리는 대신** 질의와 가까운 chunk 를 고른다.
앞부분부터 자르면 뒤쪽 chunk 는 LLM 에 아예 전달되지 않아 근거가 될 기회조차 없다.

Chroma Cloud 가 설정된 경우에만 임베딩 검색을 쓰고, 없거나 실패하면 keyword 로 되돌아간다.
Chroma 연결 실패가 파이프라인을 멈춰서는 안 된다.
"""

from __future__ import annotations

import re

from app.config import Settings, get_settings
from app.llm.base import RunContext
from app.models.contracts import Chunk
from app.services import textutil

# 프롬프트에서 chunk 앞에 붙는 머리말("[chunk-01 | 페이지 3]\n")의 넉넉한 상한
BLOCK_OVERHEAD_CHARS = 32

# Chroma 컬렉션 이름 규칙: 영숫자로 시작·끝, 3~63자, [a-zA-Z0-9._-]
_COLLECTION_SAFE = re.compile(r"[^a-zA-Z0-9._-]")

# 임베딩 검색 자체의 지연이 데모를 막지 않도록 한 문서당 상한을 둔다.
MAX_INDEXED_CHUNKS = 500


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


class ChromaRetriever(Retriever):
    """Chroma Cloud 임베딩 검색.

    실패하면 `RetrievalError` 를 던진다. 되돌리기는 `select_chunks` 가 담당한다.
    """

    name = "chroma"

    def __init__(self, settings: Settings) -> None:
        try:
            import chromadb
        except ImportError as exc:  # pragma: no cover - 설치 환경 문제
            raise RetrievalError(
                "chromadb 패키지가 설치되어 있지 않습니다. requirements.txt 를 설치하세요."
            ) from exc

        try:
            self._client = chromadb.CloudClient(
                tenant=settings.chroma_tenant,
                database=settings.chroma_database,
                api_key=settings.chroma_api_key,
            )
        except Exception as exc:  # noqa: BLE001 - 어떤 실패든 데모를 멈추면 안 된다
            raise RetrievalError(f"Chroma Cloud 에 연결하지 못했습니다: {exc}") from exc

    def rank(self, chunks: list[Chunk], query: str, namespace: str = "") -> list[str]:
        if not query.strip():
            # 질의가 없으면 임베딩 검색으로 얻을 것이 없다. 문서 순서가 최선이다.
            return [chunk.id for chunk in chunks]

        indexed = chunks[:MAX_INDEXED_CHUNKS]
        try:
            collection = self._client.get_or_create_collection(name=_collection_name(namespace))
            collection.upsert(
                ids=[chunk.id for chunk in indexed],
                documents=[chunk.text for chunk in indexed],
                metadatas=[{"page": chunk.page, "index": chunk.index} for chunk in indexed],
            )
            result = collection.query(query_texts=[query], n_results=len(indexed))
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
    name = f"audiencedeck-{base}"[:63]
    return name if name[-1].isalnum() else name + "0"


def _query_terms(query: str) -> list[str]:
    return [term for term in re.split(r"[\s,]+", query.strip()) if term]


def build_retriever(settings: Settings | None = None) -> Retriever:
    """설정에 맞는 retriever 를 만든다. 어떤 실패든 keyword 로 떨어진다."""
    settings = settings or get_settings()
    if not settings.chroma_enabled:
        return KeywordRetriever()
    try:
        return ChromaRetriever(settings)
    except RetrievalError:
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
    retriever = retriever or build_retriever()

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
