"""렌더링한 원본/결과 슬라이드를 픽셀로 대조해 "달라진 자리"를 네모로 돌려준다.

화면(`frontend/components/SourceCompare.tsx`)이 이 네모를 슬라이드 이미지 위에 그대로 얹는다.
결과 슬라이드는 원본 슬라이드의 **글만** 갈아 끼운 것이라(`export_pptx._rewrite_slide`) 두 렌더의
좌표계가 같다 — 그래서 네모 한 벌이 좌우 양쪽에 함께 맞고, 눈이 같은 자리를 오가며 비교한다.

**왜 도형 좌표가 아니라 픽셀인가.** export 가 무엇을 바꿨는지 계산해서 그리면 export 규칙이
바뀔 때 화면이 조용히 거짓말을 한다. 실제로 구운 그림끼리 대조하면 글자 크기가 줄어 줄바꿈이
달라진 것처럼 "규칙에는 없지만 눈에는 보이는" 변화까지 잡힌다. 도형 좌표는 잡아낸 네모에
**이름을 붙일 때만** 쓴다(제목인가 본문인가).

Pillow 가 없어도 앱은 뜬다. 네모가 없으면 화면은 표시 없는 슬라이드 이미지로 되돌아간다.
"""

from __future__ import annotations

import io
import logging

from app.services import export_pptx

try:  # pragma: no cover - python-pptx 가 Pillow 를 끌고 오므로 설치 환경에서는 항상 성공한다
    from PIL import Image, ImageChops

    PIL_AVAILABLE = True
except ImportError:  # pragma: no cover - 의존성이 빠진 환경
    PIL_AVAILABLE = False

_log = logging.getLogger(__name__)

# 1280x720 렌더를 격자로 눌러서 본다. 한 칸이 20x20px 라 글자 한 줄은 잡히고 안티앨리어싱
# 잡음은 묻힌다. 격자를 잘게 쪼갤수록 네모가 글자마다 흩어져 오히려 읽기 어려워진다.
_COLS = 64
_ROWS = 36
_PIXEL_THRESHOLD = 40  # 0~255. PNG 라 압축 잡음이 없어 낮게 잡아도 된다.
_CELL_RATIO = 0.02  # 한 칸의 2% 가 바뀌면 그 칸은 "바뀐 칸"
_MIN_CELLS = 4  # 점 하나짜리는 버린다 (렌더러가 매번 1px 씩 흔들리는 자리가 있다)


def _changed_cells(before: bytes, after: bytes) -> set[tuple[int, int]]:
    """두 PNG 를 겹쳐 보고 달라진 격자 칸을 모은다."""
    left = Image.open(io.BytesIO(before)).convert("L")
    right = Image.open(io.BytesIO(after)).convert("L")
    if left.size != right.size:
        # 원본이 4:3 인데 결과가 16:9 인 경우는 없다(같은 파일에서 나온다). 방어용.
        right = right.resize(left.size)

    mask = ImageChops.difference(left, right).point(
        lambda value: 255 if value > _PIXEL_THRESHOLD else 0
    )
    # BOX 축소는 블록 평균이라, 0/255 마스크에서는 결과값 자체가 "그 칸이 바뀐 비율 x255" 다.
    grid = mask.resize((_COLS, _ROWS), Image.BOX)
    return {
        (x, y)
        for y in range(_ROWS)
        for x in range(_COLS)
        if grid.getpixel((x, y)) >= _CELL_RATIO * 255
    }


def _grow(cells: set[tuple[int, int]]) -> set[tuple[int, int]]:
    """한 칸씩 부풀린다. 여백을 주는 동시에, 줄 사이가 뜬 문단을 한 덩어리로 묶는다."""
    return {
        (x + dx, y + dy)
        for x, y in cells
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
        if 0 <= x + dx < _COLS and 0 <= y + dy < _ROWS
    }


def _clusters(cells: set[tuple[int, int]]) -> list[set[tuple[int, int]]]:
    """이어진 칸끼리 묶는다 (8방향)."""
    remaining = set(cells)
    groups: list[set[tuple[int, int]]] = []
    while remaining:
        stack = [remaining.pop()]
        group = set(stack)
        while stack:
            x, y = stack.pop()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    neighbour = (x + dx, y + dy)
                    if neighbour in remaining:
                        remaining.remove(neighbour)
                        group.add(neighbour)
                        stack.append(neighbour)
        groups.append(group)
    return groups


def _named_rects(template: bytes, page: int) -> list[tuple[str, tuple[float, float, float, float]]]:
    """원본 슬라이드에서 제목·본문 상자의 자리(0~1 비율).

    export 가 실제로 글을 갈아 끼우는 그 도형들을 그대로 쓴다 — 이름이 export 동작과
    어긋나면 안 되므로 `export_pptx` 의 선택 규칙을 재구현하지 않고 빌려 온다.
    """
    from pptx import Presentation  # noqa: PLC0415 - python-pptx 없는 환경을 위해 늦게 부른다

    presentation = Presentation(io.BytesIO(template))
    slides = list(presentation.slides)
    if not 1 <= page <= len(slides):
        return []

    slide = slides[page - 1]
    width = presentation.slide_width or 1
    height = presentation.slide_height or 1

    title = export_pptx._title_shape(slide)  # noqa: SLF001 - export 와 같은 도형을 가리켜야 한다
    body = export_pptx._body_shape(slide, title)  # noqa: SLF001

    rects: list[tuple[str, tuple[float, float, float, float]]] = []
    for name, shape in (("제목", title), ("본문", body)):
        if shape is None or not shape.width or not shape.height:
            continue
        rects.append(
            (
                name,
                (
                    (shape.left or 0) / width,
                    (shape.top or 0) / height,
                    shape.width / width,
                    shape.height / height,
                ),
            )
        )
    return rects


def _box(cells: set[tuple[int, int]], label: str) -> dict:
    """칸 뭉치를 감싸는 네모 (0~1 비율). 한 칸씩 여유를 준다."""
    xs = [x for x, _ in cells]
    ys = [y for _, y in cells]
    left = max(min(xs) - 1, 0)
    top = max(min(ys) - 1, 0)
    right = min(max(xs) + 2, _COLS)
    bottom = min(max(ys) + 2, _ROWS)
    return {
        "x": left / _COLS,
        "y": top / _ROWS,
        "w": (right - left) / _COLS,
        "h": (bottom - top) / _ROWS,
        "label": label,
    }


def regions(before: bytes, after: bytes, template: bytes | None, page: int) -> list[dict]:
    """달라진 자리 목록. 좌표는 슬라이드 폭·높이에 대한 0~1 비율이다.

    **도형 단위로 먼저 가른다.** 픽셀만 보고 이어 붙이면 제목과 본문이 한 덩어리가 되어
    슬라이드 절반을 통째로 덮는 네모 하나가 나온다 — 그건 "어디가 바뀌었나"를 알려 주지 못한다.
    export 가 글을 갈아 끼우는 도형(제목·본문) 안의 변화는 그 도형 몫으로 따로 묶고, 어느
    도형에도 안 걸린 변화만 이어 붙여 묶는다. 네모는 도형 자리가 아니라 **실제로 달라진 칸**을
    감싸므로, 도형이 커도 네모는 바뀐 줄에만 붙는다.

    `template`/`page` 는 가르고 이름 붙이는 데만 쓴다. 없으면 이어 붙이기만 한다.
    실패는 빈 목록으로 끝낸다 — 표시가 없다고 대조 화면이 멈추면 안 된다.
    """
    if not PIL_AVAILABLE:
        return []

    try:
        cells = _changed_cells(before, after)
    except Exception:  # noqa: BLE001 - 렌더 결과는 통제 밖이다
        _log.warning("슬라이드 대조에 실패했습니다", exc_info=True)
        return []

    rects: list = []
    if template is not None:
        try:
            rects = _named_rects(template, page)
        except Exception:  # noqa: BLE001 - 원본 PPTX 형식은 통제 밖이다
            _log.warning("원본 도형 좌표를 읽지 못했습니다", exc_info=True)

    found: list[dict] = []
    for name, (rx, ry, rw, rh) in rects:
        inside = {
            (x, y)
            for x, y in cells
            # 칸 한가운데가 도형 안에 들어오면 그 도형 몫이다.
            if rx <= (x + 0.5) / _COLS <= rx + rw and ry <= (y + 0.5) / _ROWS <= ry + rh
        }
        if len(inside) < _MIN_CELLS:
            continue
        cells -= inside
        found.append(_box(inside, name))

    # 원본에 본문 상자가 없으면(표만 있는 장 등) export 는 빈 자리에 새 글상자를 만든다.
    # 도형을 아예 못 읽은 경우(rects 가 빔)는 "없다"고 단정하지 않는다.
    had_body = not rects or any(name == "본문" for name, _ in rects)
    for group in _clusters(_grow(cells)):
        if len(group) < _MIN_CELLS:
            continue
        # export 는 맨 아래에 "원문 근거" 줄을 새로 얹는다 (`_rewrite_slide`).
        top = min(y for _, y in group) / _ROWS
        if top > 0.88:
            label = "원문 근거 추가"
        else:
            label = "본문 추가" if not had_body else "변경"
        found.append(_box(group, label))

    # 위에서 아래로. 화면이 매기는 번호가 읽는 순서와 같아야 한다.
    found.sort(key=lambda item: (item["y"], item["x"]))
    return found
