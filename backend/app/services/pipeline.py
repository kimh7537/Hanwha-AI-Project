"""파이프라인 오케스트레이션: 문서 -> 분석 -> 변환 -> 설계 -> 지원 -> 검증.

단일 원본 원칙(docs/00-overview.md): 모든 단계는 원문이 아니라 앞 단계의 출력을 입력으로 받는다.
어느 단계에서 LLM 이 실패해도 휴리스틱으로 계속 진행하며, 그 사실은 meta.fallback_used 로 남는다.
"""

from __future__ import annotations

import time

from app.llm.base import RunContext
from app.llm.factory import build_provider
from app.models.contracts import (
    DocumentMeta,
    GenerateResponse,
    PipelineMeta,
    PresentationRequest,
    PresentationSupport,
    SlideDeck,
    SourceAnalysis,
    VerificationReport,
)
from app.services import analyzer, audience, planner, support, verifier
from app.services.chunking import build_chunks
from app.services.document_parser import PageText, parse_document
from app.services.store import StoredDocument, store


def build_document(filename: str, data: bytes) -> StoredDocument:
    """업로드 파일을 파싱하고 chunk 로 나눠 저장 가능한 형태로 만든다."""
    pages = parse_document(filename, data)
    chunks = build_chunks(pages)
    meta = DocumentMeta(
        document_id=store.new_document_id(),
        filename=filename,
        page_count=len(pages),
        char_count=sum(len(page.text) for page in pages),
        chunk_count=len(chunks),
    )
    return StoredDocument(meta=meta, chunks=chunks)


def build_document_from_text(text: str, filename: str = "sample.txt") -> StoredDocument:
    """이미 텍스트를 가지고 있을 때 (테스트·데모 스크립트용)."""
    return build_document(filename, text.encode("utf-8"))


def generate(
    document: StoredDocument,
    request: PresentationRequest,
    ctx: RunContext | None = None,
) -> GenerateResponse:
    """모듈 A~E 를 순서대로 실행한다."""
    started = time.perf_counter()
    ctx = ctx or RunContext(provider=build_provider())

    analysis: SourceAnalysis = analyzer.analyze(
        document.chunks, request, ctx, namespace=document.meta.document_id
    )
    content = audience.transform(analysis, request, ctx)
    deck: SlideDeck = planner.plan(content, analysis, request, ctx)
    presentation_support: PresentationSupport = support.build_support(
        deck, content, analysis, request, ctx
    )
    report: VerificationReport = verifier.verify(deck, presentation_support, analysis, request)

    response = GenerateResponse(
        presentation_id=store.new_presentation_id(),
        document=document.meta,
        request=request,
        source_analysis=analysis,
        audience_content=content,
        slide_deck=deck,
        presentation_support=presentation_support,
        verification_report=report,
        meta=PipelineMeta(
            provider=ctx.provider.name,
            fallback_used=ctx.fallback_used,
            fallback_reason=ctx.fallback_reason,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        ),
    )
    return response


def run_pipeline(
    text: str, filename: str, request: PresentationRequest
) -> GenerateResponse:
    """텍스트 하나로 전체 파이프라인을 도는 진입점 (demo-check 스킬이 사용)."""
    document = build_document_from_text(text, filename)
    store.save_document(document)
    response = generate(document, request)
    store.save_presentation(response)
    return response


__all__ = [
    "PageText",
    "build_document",
    "build_document_from_text",
    "generate",
    "run_pipeline",
]
