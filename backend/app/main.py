"""FastAPI 앱 진입점.

API 키는 백엔드에만 둔다. 모든 LLM 호출은 여기서만 일어난다 (docs/08-api-and-env.md).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import documents, presentations
from app.config import get_settings
from app.llm.factory import build_provider

app = FastAPI(
    title="AudienceDeck AI",
    description="기술문서를 청중에 맞춰 재구성하고 원문 근거로 검증하는 발표 지원 API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # PPTX 다운로드의 파일명은 Content-Disposition 에 담긴다. 노출하지 않으면
    # 브라우저 JS 가 읽지 못해 파일명이 사라진다.
    expose_headers=["Content-Disposition"],
)

app.include_router(documents.router)
app.include_router(presentations.router)


@app.get("/api/health")
def health() -> dict[str, object]:
    """데모 중 어떤 경로로 동작 중인지 화면에서 확인할 수 있게 한다."""
    settings = get_settings()
    provider = build_provider(settings)
    return {
        "status": "ok",
        "provider": provider.name,
        "llm_enabled": provider.available,
        "chroma_enabled": settings.chroma_enabled,
    }
