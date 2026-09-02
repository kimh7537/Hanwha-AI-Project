"""환경변수 설정. 키가 없어도 mock 으로 항상 동작해야 한다 (docs/08-api-and-env.md)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent

# 개발용 출처. 배포해도 로컬에서 같은 백엔드를 붙여 볼 수 있어야 하므로 항상 남긴다.
# 3001 은 3000 이 이미 쓰이고 있을 때 `next dev` 가 알아서 옮겨 가는 자리다.
LOCAL_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
)

# .env 는 저장소 루트 또는 backend/ 어느 쪽에 두어도 읽는다.
for candidate in (ROOT_DIR / ".env", BACKEND_DIR / ".env"):
    if candidate.exists():
        load_dotenv(candidate, override=False)


def _clean(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


@dataclass
class Settings:
    llm_provider: str = field(default_factory=lambda: _clean("LLM_PROVIDER", "mock").lower() or "mock")
    llm_api_key: str = field(default_factory=lambda: _clean("LLM_API_KEY"))
    llm_model: str = field(default_factory=lambda: _clean("LLM_MODEL"))
    chroma_api_key: str = field(default_factory=lambda: _clean("CHROMA_API_KEY"))
    chroma_tenant: str = field(default_factory=lambda: _clean("CHROMA_TENANT"))
    chroma_database: str = field(default_factory=lambda: _clean("CHROMA_DATABASE"))
    # 배포한 프론트엔드 주소. 여럿이면 쉼표로 잇는다. 비어 있으면 로컬에서만 부를 수 있다.
    extra_origins: str = field(default_factory=lambda: _clean("ALLOWED_ORIGINS"))
    fixtures_dir: Path = field(default_factory=lambda: BACKEND_DIR / "fixtures")

    # 프롬프트에 넣는 원문 길이 상한 (docs/10-quality-safety.md)
    max_prompt_chars: int = 12000

    @property
    def chroma_enabled(self) -> bool:
        return bool(self.chroma_api_key and self.chroma_tenant and self.chroma_database)

    @property
    def allowed_origins(self) -> list[str]:
        """CORS 로 허용할 출처.

        브라우저는 Origin 을 글자 그대로 대조한다 — 끝의 `/` 하나면 배포한 화면이 통째로
        막히고, 화면에는 "백엔드에 연결할 수 없습니다"만 뜬다. 여기서 떼어 둔다.
        """
        extra = [origin.strip().rstrip("/") for origin in self.extra_origins.split(",")]
        return [*LOCAL_ORIGINS, *(origin for origin in extra if origin)]


def get_settings() -> Settings:
    """매 호출마다 환경변수를 다시 읽는다 (테스트에서 monkeypatch 하기 쉽도록)."""
    return Settings()
