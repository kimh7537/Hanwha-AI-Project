from __future__ import annotations

import json
from pathlib import Path

import pytest

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
