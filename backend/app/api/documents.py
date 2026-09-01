"""POST /api/documents — 업로드 및 chunk 생성 (docs/08-api-and-env.md)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Response, UploadFile

from app.models.contracts import DocumentResponse
from app.services import render_slides
from app.services.document_parser import DocumentError
from app.services.pipeline import build_document
from app.services.store import store

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
# PPTX 용량은 대부분 이미지다. 우리는 텍스트만 쓰므로 상한을 따로 둔다.
MAX_PPTX_UPLOAD_BYTES = 30 * 1024 * 1024


@router.post("", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...)) -> DocumentResponse:
    data = await file.read()

    is_pptx = Path(file.filename or "").suffix.lower() == ".pptx"
    limit = MAX_PPTX_UPLOAD_BYTES if is_pptx else MAX_UPLOAD_BYTES

    if len(data) > limit:
        raise HTTPException(
            status_code=413,
            detail=f"파일이 너무 큽니다. {limit // (1024 * 1024)}MB 이하 문서를 사용해 주세요.",
        )

    try:
        document = build_document(file.filename or "document.txt", data)
    except DocumentError as exc:
        # 사용자에게 그대로 보여줘도 되는 한국어 메시지다
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not document.chunks:
        raise HTTPException(
            status_code=400,
            detail="문서에서 근거로 쓸 내용을 찾지 못했습니다. 내용이 있는 문서를 업로드해 주세요.",
        )

    store.save_document(document)
    return DocumentResponse(
        document=document.meta, chunks=document.chunks, pages=document.pages
    )


@router.get("/{document_id}/slides/{page}")
def document_slide(document_id: str, page: int) -> Response:
    """업로드한 원본 PPTX 의 슬라이드 한 장을 PNG 로 내려준다 (원본과 결과 대조 화면용).

    글자만 옮겨서는 표·도형·배경이 어떻게 바뀌었는지 보이지 않는다. 원본 파일을 그대로
    렌더링해야 "무엇이 달라졌나"가 눈으로 잡힌다.
    """
    document = store.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

    # source 는 업로드가 PPTX 였을 때만 채워진다 (services/pipeline.build_document).
    if not document.source:
        raise HTTPException(
            status_code=404,
            detail="슬라이드 이미지는 PPTX 를 업로드한 경우에만 제공됩니다.",
        )

    return slide_png_response(f"doc:{document_id}", document.source, page)


def slide_png_response(cache_key: str, data: bytes, number: int) -> Response:
    """PPTX 를 렌더링해 1-based `number` 번째 슬라이드를 PNG 응답으로 만든다."""
    if not render_slides.available():
        raise HTTPException(
            status_code=503,
            detail="이 PC 에서는 슬라이드 이미지를 만들 수 없습니다. 글자 비교로 확인해 주세요.",
        )

    try:
        images = render_slides.render(cache_key, data)
    except Exception as exc:  # noqa: BLE001 - PowerPoint 는 통제 밖이다
        raise HTTPException(
            status_code=503,
            detail="슬라이드 이미지를 만들지 못했습니다. 글자 비교로 확인해 주세요.",
        ) from exc

    if not 1 <= number <= len(images):
        raise HTTPException(status_code=404, detail="해당 슬라이드가 없습니다.")

    return Response(
        content=images[number - 1],
        media_type="image/png",
        # 같은 덱의 같은 장은 내용이 바뀌지 않는다. 브라우저가 다시 받지 않게 한다.
        headers={"Cache-Control": "private, max-age=3600"},
    )
