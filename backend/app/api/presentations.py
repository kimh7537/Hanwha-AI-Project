"""발표 생성/검증/조회 API (docs/08-api-and-env.md)."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Response

from app.models.contracts import (
    GenerateRequest,
    GenerateResponse,
    VerificationReport,
    VerifyRequest,
)
from app.services import export_pptx, verifier
from app.services.pipeline import generate
from app.services.store import store

PPTX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
)

router = APIRouter(prefix="/api/presentations", tags=["presentations"])


@router.post("/generate", response_model=GenerateResponse)
def generate_presentation(payload: GenerateRequest) -> GenerateResponse:
    document = store.get_document(payload.document_id)
    if document is None:
        raise HTTPException(
            status_code=404,
            detail="문서를 찾을 수 없습니다. 문서를 다시 업로드해 주세요.",
        )

    response = generate(document, payload.request)
    store.save_presentation(response)
    return response


@router.post("/verify", response_model=VerificationReport)
def verify_presentation(payload: VerifyRequest) -> VerificationReport:
    """저장된 결과를 다시 검증하거나, 직접 넘긴 덱을 검증한다."""
    if payload.presentation_id:
        stored = store.get_presentation(payload.presentation_id)
        if stored is None:
            raise HTTPException(status_code=404, detail="발표 결과를 찾을 수 없습니다.")
        report = verifier.verify(
            stored.slide_deck,
            stored.presentation_support,
            stored.source_analysis,
            stored.request,
        )
        stored.verification_report = report
        store.save_presentation(stored)
        return report

    if not (payload.document_id and payload.slide_deck and payload.request):
        raise HTTPException(
            status_code=400,
            detail="presentation_id 또는 (document_id, request, slide_deck) 조합이 필요합니다.",
        )

    document = store.get_document(payload.document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

    # 넘겨받은 덱을 검증하려면 그 문서의 SourceAnalysis 가 필요하다.
    # 같은 문서로 생성된 결과가 있으면 그 분석을 재사용한다.
    analysis = None
    for stored in store._presentations.values():  # noqa: SLF001 - MVP 범위의 인메모리 저장소
        if stored.document.document_id == payload.document_id:
            analysis = stored.source_analysis
            break

    if analysis is None:
        raise HTTPException(
            status_code=409,
            detail="이 문서로 생성된 분석 결과가 없습니다. 먼저 발표자료를 생성해 주세요.",
        )

    from app.models.contracts import PresentationSupport

    return verifier.verify(
        payload.slide_deck,
        payload.presentation_support or PresentationSupport(),
        analysis,
        payload.request,
    )


@router.get("/{presentation_id}", response_model=GenerateResponse)
def get_presentation(presentation_id: str) -> GenerateResponse:
    stored = store.get_presentation(presentation_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="발표 결과를 찾을 수 없습니다.")
    return stored


@router.get("/{presentation_id}/export/pptx")
def export_presentation_pptx(presentation_id: str) -> Response:
    """저장된 결과를 PPTX 로 내려준다.

    새 문장을 만들지 않고 이미 검증을 마친 결과를 그대로 배치하므로 재생성이 필요 없다.
    python-pptx 가 없는 환경에서도 앱은 동작해야 하므로 실패는 503 + 한국어 안내로 끝낸다.
    """
    stored = store.get_presentation(presentation_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="발표 결과를 찾을 수 없습니다.")

    try:
        content = export_pptx.build_pptx(stored)
    except export_pptx.PptxUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    filename = export_pptx.filename_for(stored)
    # 파일명이 한국어라 ASCII 로만 쓸 수 없다. RFC 5987 형식을 함께 준다.
    fallback = f"{presentation_id}.pptx"
    disposition = (
        f'attachment; filename="{fallback}"; filename*=UTF-8\'\'{quote(filename)}'
    )

    return Response(
        content=content,
        media_type=PPTX_MEDIA_TYPE,
        headers={"Content-Disposition": disposition},
    )
