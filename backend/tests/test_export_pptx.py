"""PPTX export (docs/04-slide-planner.md).

export 는 새 문장을 만들지 않는다. 화면에 보이는 내용이 파일 안에도 그대로 있어야 한다.
"""

from __future__ import annotations

import base64
import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Inches

from app.api.presentations import PPTX_MEDIA_TYPE
from app.main import app
from app.models.contracts import GenerateResponse, SourceEvidence
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


# --- 원본 PPTX 형식 지키기 --------------------------------------------------
#
# 입력이 PPTX 면 export 는 새 파일을 그리지 않고 원본 위에 얹는다. 원본의 이미지·표는
# 텍스트 프레임이 아니므로 손대지 않는 것이 규칙이고, 이 테스트가 그 규칙을 지킨다.

_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _template_with_picture_and_table() -> bytes:
    """2장짜리 원본. 2장은 표·그림만 있고 본문 텍스트 상자가 없다 (빈 자리 탐색 경로)."""
    presentation = Presentation()

    first = presentation.slides.add_slide(presentation.slide_layouts[1])
    first.shapes.title.text = "원본 제목"
    first.placeholders[1].text_frame.text = "원본 본문"

    second = presentation.slides.add_slide(presentation.slide_layouts[5])
    second.shapes.title.text = "원본 표 슬라이드"
    second.shapes.add_table(2, 2, Inches(0.6), Inches(1.8), Inches(4.0), Inches(1.2))
    second.shapes.add_picture(
        io.BytesIO(_PIXEL_PNG), Inches(5.2), Inches(1.8), Inches(2.0), Inches(1.2)
    )

    buffer = io.BytesIO()
    presentation.save(buffer)
    return buffer.getvalue()


def _count_visuals(presentation: Presentation) -> tuple[int, int]:
    pictures = tables = 0
    for slide in presentation.slides:
        for shape in slide.shapes:
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                pictures += 1
            if getattr(shape, "has_table", False):
                tables += 1
    return pictures, tables


@pytest.fixture()
def two_slide_result(result: GenerateResponse) -> GenerateResponse:
    """생성 슬라이드 2장이 원본 1·2장에서 왔다고 두고 근거를 다시 건다."""
    result.source_analysis.source_evidence = [
        SourceEvidence(id="chunk-01", text="", page=1),
        SourceEvidence(id="chunk-02", text="", page=2),
    ]
    result.slide_deck.slides = result.slide_deck.slides[:2]
    for slide_data, ref in zip(result.slide_deck.slides, ["chunk-01", "chunk-02"]):
        slide_data.source_refs = [ref]
    return result


def test_original_pictures_and_tables_survive(two_slide_result: GenerateResponse) -> None:
    """사용자가 만들어 둔 이미지·표가 사라지지 않는다 — 이 모듈의 존재 이유."""
    template = _template_with_picture_and_table()
    assert _count_visuals(_open(template)) == (1, 1)

    exported = _open(export_pptx.build_pptx(two_slide_result, template=template))
    assert _count_visuals(exported) == (1, 1)


def test_generated_text_replaces_the_original_text(
    two_slide_result: GenerateResponse,
) -> None:
    """형식만 남기고 글은 청중용으로 바뀌어야 한다. 표만 있는 슬라이드도 마찬가지."""
    template = _template_with_picture_and_table()
    text = _all_text(_open(export_pptx.build_pptx(two_slide_result, template=template)))

    assert "원본 본문" not in text
    for slide_data in two_slide_result.slide_deck.slides:
        for bullet in slide_data.bullets:
            assert bullet in text


def test_title_only_slide_keeps_the_title_in_its_title_box(
    two_slide_result: GenerateResponse,
) -> None:
    """제목 상자에 본문 bullet 이 들어가면 안 된다.

    `shapes.title` 은 호출할 때마다 새 proxy 라 `is` 로 거르면 제목이 본문 후보가 되고,
    표만 있는 슬라이드에서는 제목 자리에 bullet 이 통째로 들어간다.
    """
    template = _template_with_picture_and_table()
    exported = _open(export_pptx.build_pptx(two_slide_result, template=template))

    slide_data = two_slide_result.slide_deck.slides[1]
    table_slide = exported.slides[2]  # 표지 → 원본 1장 → 표 슬라이드
    assert table_slide.shapes.title.text_frame.text == slide_data.title


def test_template_keeps_its_own_slide_size(two_slide_result: GenerateResponse) -> None:
    """원본이 4:3 이면 부록 슬라이드도 4:3 이어야 한다. 16:9 로 늘리면 원본이 잘린다."""
    template = _template_with_picture_and_table()
    source = _open(template)
    exported = _open(export_pptx.build_pptx(two_slide_result, template=template))

    assert exported.slide_width == source.slide_width
    assert exported.slide_height == source.slide_height


def test_broken_template_falls_back_to_a_new_deck(result: GenerateResponse) -> None:
    """원본을 못 열어도 다운로드는 성공해야 한다."""
    exported = _open(export_pptx.build_pptx(result, template=b"not a pptx"))
    assert len(exported.slides) > 1


def test_uploaded_pptx_is_kept_for_export(customer_request) -> None:
    """plumbing: 원본 바이트를 들고 있지 않으면 얹을 것이 없다."""
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "sample_document.pptx"
    if not fixture.exists():
        pytest.skip("scripts/build_sample_pptx.py 로 fixture 를 먼저 만들어 주세요.")

    data = fixture.read_bytes()
    document = build_document("sample_document.pptx", data)
    assert document.source == data

    # TXT 입력은 얹을 원본이 없다
    assert build_document("sample.txt", b"a" * 200).source is None

    exported = _open(export_pptx.build_pptx(generate(document, customer_request), template=data))
    assert _count_visuals(exported)[1] >= 1  # 원본의 성능 표가 살아 있다
