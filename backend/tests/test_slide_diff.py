"""픽셀 대조가 "달라진 자리"를 실제로 짚는지 (app/services/slide_diff.py).

원본과 결과 슬라이드는 렌더링 결과가 대부분 같고 글자 자리만 다르다. 여기서 검사할 것은
"바뀐 데를 찾느냐"와 "안 바뀐 데를 안 찾느냐" 두 가지다 — 후자가 깨지면 화면이 슬라이드
전체에 빨간 네모를 씌워 아무것도 알려 주지 못한다.
"""

from __future__ import annotations

import io

import pytest

from app.services import slide_diff

pytest.importorskip("PIL", reason="Pillow 가 없으면 변경 표시 자체가 꺼진다")
from PIL import Image, ImageDraw  # noqa: E402

_W, _H = 1280, 720


def _png(boxes: list[tuple[int, int, int, int]]) -> bytes:
    image = Image.new("RGB", (_W, _H), "white")
    draw = ImageDraw.Draw(image)
    for box in boxes:
        draw.rectangle(box, fill="black")
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def test_identical_slides_have_no_regions() -> None:
    same = _png([(100, 100, 400, 200)])
    assert slide_diff.regions(same, same, None, 1) == []


def test_changed_area_is_boxed_and_the_rest_is_not() -> None:
    before = _png([(100, 100, 400, 200)])
    after = _png([(100, 100, 400, 200), (700, 400, 1000, 500)])

    found = slide_diff.regions(before, after, None, 1)
    assert len(found) == 1

    box = found[0]
    # 네모가 바뀐 자리를 감싼다 (격자 한 칸 = 20px 이라 여유를 둔다).
    assert box["x"] * _W <= 700 and (box["x"] + box["w"]) * _W >= 1000
    assert box["y"] * _H <= 400 and (box["y"] + box["h"]) * _H >= 500
    # 그러면서 슬라이드 전체를 덮지는 않는다 — 안 바뀐 왼쪽 위 도형은 밖에 있어야 한다.
    assert box["x"] * _W > 400
    assert box["w"] < 0.5 and box["h"] < 0.5


def test_two_separate_changes_stay_separate_and_read_top_down() -> None:
    before = _png([])
    after = _png([(100, 80, 300, 140), (100, 500, 300, 560)])

    found = slide_diff.regions(before, after, None, 1)
    assert len(found) == 2
    # 화면이 매기는 번호가 읽는 순서와 같아야 한다.
    assert found[0]["y"] < found[1]["y"]


def test_single_pixel_noise_is_ignored() -> None:
    """렌더러가 매번 1px 씩 흔들리는 자리를 변경으로 보고하면 표시가 쓸모없어진다."""
    before = _png([])
    after = _png([(640, 360, 641, 361)])
    assert slide_diff.regions(before, after, None, 1) == []
