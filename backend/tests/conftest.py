from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

# 테스트는 절대 실 API 를 부르지 않는다.
# .env 에 실 provider/Chroma 가 설정돼 있어도 여기서 덮어쓴다 — 켜져 있으면 테스트가
# 느려지고 비용이 들며, LLM 출력이 매번 달라 휴리스틱 단정이 깨진다.
# config.load_dotenv 는 override=False 라 먼저 넣어 둔 이 값이 이긴다.
os.environ["LLM_PROVIDER"] = "mock"
for _var in ("LLM_API_KEY", "CHROMA_API_KEY", "CHROMA_TENANT", "CHROMA_DATABASE"):
    os.environ[_var] = ""

from app.models.contracts import Chunk, PresentationRequest, SourceAnalysis
from app.services.chunking import build_chunks
from app.services.document_parser import parse_document

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def sample_text() -> str:
    return (FIXTURES / "sample_document.txt").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def chunks(sample_text: str) -> list[Chunk]:
    return build_chunks(parse_document("sample_document.txt", sample_text.encode("utf-8")))


@pytest.fixture()
def customer_request() -> PresentationRequest:
    return PresentationRequest(
        audience="customer",
        purpose="technical_explanation",
        duration_minutes=5,
        keywords=["정확도", "도입 효과"],
        style="persuasive",
        preserve_original_terms=True,
        slide_count=5,
    )


@pytest.fixture()
def analysis() -> SourceAnalysis:
    return SourceAnalysis(**load_fixture("source_analysis.json"))
