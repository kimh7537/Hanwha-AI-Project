"""FastAPI 앱 진입점.

API 키는 백엔드에만 둔다. 모든 LLM 호출은 여기서만 일어난다 (docs/08-api-and-env.md).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import audiences, documents, presentations
from app.config import get_settings
from app.llm.factory import build_provider
from app.services import render_slides, retrieval

app = FastAPI(
    title="AudienceDeck AI",
    description="기술문서를 청중에 맞춰 재구성하고 원문 근거로 검증하는 발표 지원 API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    # 배포하면 화면과 API 가 다른 도메인에 있다. 허용할 출처를 코드에 박아 두면 배포할
    # 때마다 이 파일을 고쳐야 하므로 `ALLOWED_ORIGINS` 로 받는다 (docs/08-api-and-env.md).
    allow_origins=get_settings().allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # PPTX 다운로드의 파일명은 Content-Disposition 에 담긴다. 노출하지 않으면
    # 브라우저 JS 가 읽지 못해 파일명이 사라진다.
    expose_headers=["Content-Disposition"],
)

app.include_router(audiences.router)
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
        # chroma_enabled 는 "세 환경변수가 채워졌는가"이고,
        # retrieval 은 "실제로 어느 검색 경로가 잡혔는가"다. 둘은 다를 수 있다.
        "chroma_enabled": settings.chroma_enabled,
        "retrieval": retrieval.build_retriever(settings).name,
        # 원본/결과를 슬라이드 이미지로 대조할 수 있는지. 없으면 화면이 글자 대조로 돌아간다.
        "render_enabled": render_slides.available(),
    }
