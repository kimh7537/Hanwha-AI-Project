"""POST /api/documents — 업로드 및 chunk 생성 (docs/08-api-and-env.md)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.contracts import DocumentResponse
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
    return DocumentResponse(document=document.meta, chunks=document.chunks)
