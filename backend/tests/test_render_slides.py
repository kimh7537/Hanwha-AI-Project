"""LibreOffice 렌더링 경로.

LibreOffice 가 깔린 PC 는 거의 없으므로(배포 컨테이너에만 있다) 여기서는 그것 없이도
확인할 수 있는 두 가지만 본다 — PDF 를 PNG 로 그리는 규칙과, 실행 파일이 없을 때의 실패.
"""

from __future__ import annotations

import io
from pathlib import Path

import fitz
import pytest
from PIL import Image

from app.services import render_slides


def test_pdf_pages_become_fixed_size_pngs(tmp_path: Path) -> None:
    """쪽 비율과 무관하게 1280×720 으로 나온다.

    PowerPoint 경로의 `Export(WIDTH, HEIGHT)` 와 같은 좌표계여야 화면의 변경 표시 네모가
    원본·결과 양쪽에 함께 맞는다. 4:3 원본이 섞여도 어긋나지 않는지 본다.
    """
    document = fitz.open()
    document.new_page(width=720, height=540)  # 4:3
    document.new_page(width=960, height=540)  # 16:9
    pdf = tmp_path / "deck.pdf"
    document.save(pdf)
    document.close()

    images = render_slides._pdf_to_pngs(pdf)

    assert len(images) == 2
    for image in images:
        with Image.open(io.BytesIO(image)) as png:
            assert png.size == (render_slides.WIDTH, render_slides.HEIGHT)


def test_missing_soffice_is_a_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """실행 파일이 없으면 API 가 503 + 한국어 안내로 바꿀 수 있는 예외로 끝난다."""
    monkeypatch.setattr(render_slides, "_soffice", lambda: None)

    with pytest.raises(RuntimeError, match="LibreOffice"):
        render_slides._render_with_soffice(b"deck")
