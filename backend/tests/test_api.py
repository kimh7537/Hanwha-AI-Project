"""API 스모크 테스트 (docs/08-api-and-env.md).

API 키 없이(mock) 전체 흐름이 끝까지 돌아야 한다.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import render_slides
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
    page_count = payload["document"]["page_count"]
    assert page_count >= 5  # 슬라이드 수
    assert payload["chunks"]
    assert payload["chunks"][0]["id"] == "chunk-01"

    # 원본 대조 화면은 "원본 슬라이드 N" 을 빠짐없이 그린다. chunk 는 쪽 경계를 넘어 묶이고
    # page 는 chunk 가 "시작한" 쪽이라 chunk 로는 이 성질이 깨진다 — 그래서 pages 를 따로 받는다.
    assert [page["page"] for page in payload["pages"]] == list(range(1, page_count + 1))
    assert {chunk["page"] for chunk in payload["chunks"]} < set(range(1, page_count + 1))


def test_slide_image_degrades_without_powerpoint(
    client: TestClient, uploaded: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """원본 대조 화면은 슬라이드 렌더링이 안 되는 PC 에서도 살아 있어야 한다.

    렌더링은 데모의 전제가 아니다(docs/10). 실패는 503 + 한국어 안내로 끝나고 화면은
    글자 비교로 되돌아간다. PowerPoint 가 있는 개발기에서도 이 경로가 도는지 봐야 하므로
    `available()` 을 꺼서 확인한다 — 테스트가 PowerPoint 를 띄우지 않게 하는 뜻도 있다.
    """
    document_id = uploaded["document"]["document_id"]

    # TXT 업로드에는 원본 PPTX 가 없다. 이때는 503 이 아니라 "PPTX 만 된다"는 404 다.
    original = client.get(f"/api/documents/{document_id}/slides/1")
    assert original.status_code == 404
    assert "PPTX" in original.json()["detail"]

    created = client.post(
        "/api/presentations/generate",
        json={
            "document_id": document_id,
            "request": {
                "audience": "executive",
                "purpose": "internal_report",
                "duration_minutes": 3,
            },
        },
    )
    assert created.status_code == 200, created.text

    monkeypatch.setattr(render_slides, "available", lambda: False)
    response = client.get(
        f"/api/presentations/{created.json()['presentation_id']}/slides/1"
    )
    assert response.status_code == 503
    assert "글자 비교" in response.json()["detail"]


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
