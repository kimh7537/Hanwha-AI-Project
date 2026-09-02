"""PPTX export (docs/04-slide-planner.md).

export 는 새 문장을 만들지 않는다. 화면에 보이는 내용이 파일 안에도 그대로 있어야 한다.
"""

from __future__ import annotations

import io
import zipfile

import pytest
from fastapi.testclient import TestClient
from pptx import Presentation

from app.api.presentations import PPTX_MEDIA_TYPE
from app.main import app
from app.models.contracts import GenerateResponse
from app.services import export_pptx
from app.services.pipeline import build_document, generate
from app.services.store import store


@pytest.fixture()
def result(sample_text: str, customer_request) -> GenerateResponse:
    document = build_document("sample_document.txt", sample_text.encode("utf-8"))
    return generate(document, customer_request)


def _open(data: bytes) -> Presentation:
    return Presentation(io.BytesIO(data))


def _all_text(presentation: Presentation) -> str:
    texts: list[str] = []
    for slide in presentation.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                texts.append(shape.text_frame.text)
    return "\n".join(texts)


def test_deck_has_cover_slides_and_appendix(result: GenerateResponse) -> None:
    presentation = _open(export_pptx.build_pptx(result))

    # 표지 1장 + 본문 + 예상 Q&A 부록 + 검증 부록
    assert len(presentation.slides) > len(result.slide_deck.slides) + 1

    text = _all_text(presentation)
    assert result.slide_deck.title in text
    for slide in result.slide_deck.slides:
        assert slide.takeaway in text


def test_bullets_are_not_truncated(result: GenerateResponse) -> None:
    """문장을 자르면 깨진 어미가 남는다. 넘칠 때는 글자 크기를 줄인다."""
    text = _all_text(_open(export_pptx.build_pptx(result)))
    for slide in result.slide_deck.slides:
        for bullet in slide.bullets:
            assert bullet in text


def test_source_refs_are_printed_on_every_slide(result: GenerateResponse) -> None:
    """데모 성공 기준 4번 — 근거는 파일에서도 따라갈 수 있어야 한다."""
    presentation = _open(export_pptx.build_pptx(result))
    # 표지 다음부터가 본문 슬라이드다
    body = list(presentation.slides)[1 : 1 + len(result.slide_deck.slides)]

    for slide_data, slide in zip(result.slide_deck.slides, body):
        text = "\n".join(
            shape.text_frame.text for shape in slide.shapes if shape.has_text_frame
        )
        assert "원문 근거:" in text
        for ref in slide_data.source_refs:
            assert ref in text


def test_speaker_notes_carry_the_script(result: GenerateResponse) -> None:
    presentation = _open(export_pptx.build_pptx(result))
    body = list(presentation.slides)[1 : 1 + len(result.slide_deck.slides)]

    scripts = {item.slide_id: item for item in result.presentation_support.scripts}
    for slide_data, slide in zip(result.slide_deck.slides, body):
        notes = slide.notes_slide.notes_text_frame.text
        script = scripts.get(slide_data.id)
        assert script is not None
        assert script.script in notes


def test_customer_deck_warns_before_publishing(result: GenerateResponse) -> None:
    """고객 청중이면 '공개 전 검토 필요' 를 색이 아니라 글자로 남긴다."""
    assert result.request.audience.value == "customer"
    assert "공개 전 검토 필요" in _all_text(_open(export_pptx.build_pptx(result)))


def test_verification_status_uses_text_label(result: GenerateResponse) -> None:
    from app.services import labels

    report = result.verification_report
    assert report is not None
    text = _all_text(_open(export_pptx.build_pptx(result)))
    assert labels.STATUS_LABELS[report.status] in text


def test_filename_drops_characters_windows_rejects(result: GenerateResponse) -> None:
    result.slide_deck.title = 'a/b:c*d?e"f<g>h|i'
    assert export_pptx.filename_for(result) == "a b c d e f g h i.pptx"


def test_filename_falls_back_to_presentation_id(result: GenerateResponse) -> None:
    result.slide_deck.title = ""
    assert export_pptx.filename_for(result) == f"{result.presentation_id}.pptx"


# --- API ------------------------------------------------------------------


@pytest.fixture()
def client() -> TestClient:
    store.clear()
    return TestClient(app)


def _generate(client: TestClient, sample_text: str) -> str:
    uploaded = client.post(
        "/api/documents",
        files={"file": ("sample_document.txt", sample_text.encode("utf-8"), "text/plain")},
    ).json()
    generated = client.post(
        "/api/presentations/generate",
        json={
            "document_id": uploaded["document"]["document_id"],
            "request": {
                "audience": "executive",
                "purpose": "internal_report",
                "duration_minutes": 5,
                "keywords": [],
                "style": "concise",
                "preserve_original_terms": True,
                "slide_count": 5,
            },
        },
    )
    assert generated.status_code == 200, generated.text
    return generated.json()["presentation_id"]


def test_export_endpoint_returns_a_real_pptx(client: TestClient, sample_text: str) -> None:
    presentation_id = _generate(client, sample_text)

    response = client.get(f"/api/presentations/{presentation_id}/export/pptx")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == PPTX_MEDIA_TYPE

    # PPTX 는 zip 이다. 실제로 열리는지까지 확인한다.
    assert zipfile.is_zipfile(io.BytesIO(response.content))
    assert len(_open(response.content).slides) > 1


def test_export_sets_a_downloadable_korean_filename(
    client: TestClient, sample_text: str
) -> None:
    presentation_id = _generate(client, sample_text)
    response = client.get(f"/api/presentations/{presentation_id}/export/pptx")

    disposition = response.headers["content-disposition"]
    assert disposition.startswith("attachment;")
    # 한국어 파일명은 ASCII 로 못 쓴다. 대체 이름과 RFC 5987 이름이 함께 있어야 한다.
    assert f'filename="{presentation_id}.pptx"' in disposition
    assert "filename*=UTF-8''" in disposition


def test_export_unknown_presentation_returns_404(client: TestClient) -> None:
    response = client.get("/api/presentations/pres-missing/export/pptx")
    assert response.status_code == 404
    assert "발표 결과를 찾을 수 없습니다" in response.json()["detail"]


def test_export_without_python_pptx_explains_in_korean(
    client: TestClient, sample_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """의존성이 빠져도 앱은 살아 있고, 다른 다운로드로 안내한다."""
    presentation_id = _generate(client, sample_text)
    monkeypatch.setattr(export_pptx, "PPTX_AVAILABLE", False)

    response = client.get(f"/api/presentations/{presentation_id}/export/pptx")
    assert response.status_code == 503
    assert "Markdown 또는 JSON 다운로드" in response.json()["detail"]
