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
from app.api.documents import render_or_503, slide_png_response
from app.services import export_pptx, slide_diff, verifier
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


@router.get("/{presentation_id}/slides/{number}")
def presentation_slide(presentation_id: str, number: int) -> Response:
    """생성된 발표자료의 슬라이드 한 장을 PNG 로 내려준다 (원본과 결과 대조 화면용).

    내려받는 PPTX 를 그대로 굽는다. 화면에 보이는 장이 곧 파일에 들어 있는 장이어야 한다.
    `number` 는 화면의 발표용 덱 기준 1-based 이며, 파일 1번은 표지라 여기서 한 장 밀어준다.
    """
    stored = store.get_presentation(presentation_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="발표 결과를 찾을 수 없습니다.")

    document = store.get_document(stored.document.document_id)

    try:
        content = export_pptx.build_pptx(stored, template=document.source if document else None)
    except export_pptx.PptxUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return slide_png_response(f"pres:{presentation_id}", content, number + 1)


@router.get("/{presentation_id}/slides/{number}/diff")
def presentation_slide_diff(presentation_id: str, number: int, page: int) -> dict:
    """원본 `page` 장과 발표용 `number` 장 사이에서 달라진 자리 (원본과 결과 대조 화면용).

    좌표는 0~1 비율이라 화면이 이미지를 어떤 크기로 그리든 그대로 얹힌다. 두 렌더가 같은
    좌표계라(원본 슬라이드의 글만 갈아 끼운다) 네모 한 벌이 좌우 양쪽에 함께 맞는다.

    렌더링은 두 번 다 캐시를 탄다 — 대조 화면이 이미 두 이미지를 띄운 뒤에 부르기 때문이다.
    """
    stored = store.get_presentation(presentation_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="발표 결과를 찾을 수 없습니다.")

    document = store.get_document(stored.document.document_id)
    if document is None or not document.source:
        raise HTTPException(
            status_code=404,
            detail="변경 표시는 PPTX 를 업로드한 경우에만 제공됩니다.",
        )

    try:
        content = export_pptx.build_pptx(stored, template=document.source)
    except export_pptx.PptxUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    originals = render_or_503(f"doc:{document.meta.document_id}", document.source)
    results = render_or_503(f"pres:{presentation_id}", content)

    # 결과 파일의 1번은 표지라 발표용 N 장은 파일의 N+1 장이다 (presentation_slide 와 같다).
    if not 1 <= page <= len(originals) or not 1 <= number + 1 <= len(results):
        raise HTTPException(status_code=404, detail="해당 슬라이드가 없습니다.")

    return {
        "regions": slide_diff.regions(
            originals[page - 1], results[number], document.source, page
        )
    }


@router.get("/{presentation_id}/export/pptx")
def export_presentation_pptx(presentation_id: str) -> Response:
    """저장된 결과를 PPTX 로 내려준다.

    새 문장을 만들지 않고 이미 검증을 마친 결과를 그대로 배치하므로 재생성이 필요 없다.
    입력이 PPTX 였으면 원본 파일 위에 얹어 원본의 이미지·표·서식을 지킨다.
    python-pptx 가 없는 환경에서도 앱은 동작해야 하므로 실패는 503 + 한국어 안내로 끝낸다.
    """
    stored = store.get_presentation(presentation_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="발표 결과를 찾을 수 없습니다.")

    # source 는 원본이 PPTX 였을 때만 채워져 있다. 문서가 없으면 새 덱으로 만든다.
    document = store.get_document(stored.document.document_id)

    try:
        content = export_pptx.build_pptx(stored, template=document.source if document else None)
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
