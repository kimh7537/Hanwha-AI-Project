"""API 스모크 테스트 (docs/08-api-and-env.md).

API 키 없이(mock) 전체 흐름이 끝까지 돌아야 한다.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.store import store


@pytest.fixture()
def client() -> TestClient:
    store.clear()
    return TestClient(app)


@pytest.fixture()
def uploaded(client: TestClient, sample_text: str) -> dict:
    response = client.post(
        "/api/documents",
        files={"file": ("sample_document.txt", sample_text.encode("utf-8"), "text/plain")},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_health_reports_provider(client: TestClient) -> None:
    payload = client.get("/api/health").json()
    assert payload["status"] == "ok"
    assert payload["provider"] == "mock"
    assert payload["llm_enabled"] is False


def test_upload_returns_chunks(uploaded: dict) -> None:
    assert uploaded["document"]["chunk_count"] == len(uploaded["chunks"])
    assert uploaded["chunks"][0]["id"] == "chunk-01"
    assert uploaded["chunks"][0]["page"] >= 1


def test_unsupported_file_returns_korean_error(client: TestClient) -> None:
    response = client.post(
        "/api/documents",
        files={"file": ("archive.zip", b"binary", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "PDF, PPTX, TXT" in response.json()["detail"]


def test_pptx_upload_produces_chunks(client: TestClient) -> None:
    """PPTX 업로드도 TXT/PDF 와 같은 chunk 계약을 만족해야 한다."""
    pptx_path = Path(__file__).resolve().parents[1] / "fixtures" / "sample_document.pptx"
    if not pptx_path.exists():
        pytest.skip("PPTX fixture 가 없습니다")

    response = client.post(
        "/api/documents",
        files={
            "file": (
                "sample_document.pptx",
                pptx_path.read_bytes(),
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            )
        },
    )
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload["document"]["page_count"] >= 5  # 슬라이드 수
    assert payload["chunks"]
    assert payload["chunks"][0]["id"] == "chunk-01"


def test_generate_returns_full_pipeline(client: TestClient, uploaded: dict) -> None:
    response = client.post(
        "/api/presentations/generate",
        json={
            "document_id": uploaded["document"]["document_id"],
            "request": {
                "audience": "customer",
                "purpose": "technical_explanation",
                "duration_minutes": 5,
                "keywords": ["정확도", "도입 효과"],
                "style": "persuasive",
                "preserve_original_terms": True,
                "slide_count": 5,
            },
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["slide_deck"]["slides"]
    assert payload["presentation_support"]["scripts"]
    assert payload["verification_report"]["summary"]
    assert payload["meta"]["provider"] == "mock"
    assert payload["meta"]["fallback_used"] is False

    for slide in payload["slide_deck"]["slides"]:
        assert slide["source_refs"]


def test_generate_with_unknown_document_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/presentations/generate",
        json={
            "document_id": "doc-missing",
            "request": {
                "audience": "customer",
                "purpose": "technical_explanation",
                "duration_minutes": 5,
                "keywords": [],
                "style": "persuasive",
                "preserve_original_terms": True,
                "slide_count": 5,
            },
        },
    )
    assert response.status_code == 404
    assert "문서를 찾을 수 없습니다" in response.json()["detail"]


def test_verify_and_fetch_by_id(client: TestClient, uploaded: dict) -> None:
    generated = client.post(
        "/api/presentations/generate",
        json={
            "document_id": uploaded["document"]["document_id"],
            "request": {
                "audience": "newcomer",
                "purpose": "education",
                "duration_minutes": 3,
                "keywords": [],
                "style": "friendly",
                "preserve_original_terms": False,
                "slide_count": None,
            },
        },
    ).json()

    presentation_id = generated["presentation_id"]

    verified = client.post(
        "/api/presentations/verify", json={"presentation_id": presentation_id}
    )
    assert verified.status_code == 200
    assert verified.json()["status"] in {"ok", "warning", "review_needed"}

    fetched = client.get(f"/api/presentations/{presentation_id}")
    assert fetched.status_code == 200
    assert fetched.json()["presentation_id"] == presentation_id


def test_verify_unknown_presentation_returns_404(client: TestClient) -> None:
    response = client.post("/api/presentations/verify", json={"presentation_id": "pres-missing"})
    assert response.status_code == 404
