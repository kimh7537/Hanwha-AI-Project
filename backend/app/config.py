"""환경변수 설정. 키가 없어도 mock 으로 항상 동작해야 한다 (docs/08-api-and-env.md)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent

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
    fixtures_dir: Path = field(default_factory=lambda: BACKEND_DIR / "fixtures")

    # 프롬프트에 넣는 원문 길이 상한 (docs/10-quality-safety.md)
    max_prompt_chars: int = 12000

    @property
    def chroma_enabled(self) -> bool:
        return bool(self.chroma_api_key and self.chroma_tenant and self.chroma_database)


def get_settings() -> Settings:
    """매 호출마다 환경변수를 다시 읽는다 (테스트에서 monkeypatch 하기 쉽도록)."""
    return Settings()
