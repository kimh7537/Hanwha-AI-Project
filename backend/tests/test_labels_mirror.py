"""화면 라벨의 유일한 출처는 frontend/lib/labels.ts 다.

PPTX 는 백엔드에서 만들어지므로 app/services/labels.py 에 같은 라벨이 한 벌 더 있다.
둘이 어긋나면 화면과 내려받은 파일의 용어가 달라지므로 여기서 대조한다.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.services import labels

LABELS_TS = Path(__file__).resolve().parents[2] / "frontend" / "lib" / "labels.ts"

MIRRORED = [
    ("AUDIENCE_LABELS", labels.AUDIENCE_LABELS),
    ("PURPOSE_LABELS", labels.PURPOSE_LABELS),
    ("STYLE_LABELS", labels.STYLE_LABELS),
    ("SEVERITY_LABELS", labels.SEVERITY_LABELS),
    ("STATUS_LABELS", labels.STATUS_LABELS),
    ("ISSUE_TYPE_LABELS", labels.ISSUE_TYPE_LABELS),
]


def _parse(name: str) -> dict[str, str]:
    source = LABELS_TS.read_text(encoding="utf-8")
    block = re.search(rf"export const {name}[^=]*=\s*\{{(.*?)\}};", source, re.DOTALL)
    assert block is not None, f"{name} 를 labels.ts 에서 찾지 못했습니다."
    return dict(re.findall(r"(\w+):\s*\"([^\"]*)\"", block.group(1)))


@pytest.mark.skipif(not LABELS_TS.exists(), reason="프론트엔드가 없는 환경")
@pytest.mark.parametrize(("name", "backend_map"), MIRRORED, ids=[n for n, _ in MIRRORED])
def test_backend_labels_match_frontend(name: str, backend_map: dict) -> None:
    expected = _parse(name)
    actual = {key.value: value for key, value in backend_map.items()}
    assert actual == expected
