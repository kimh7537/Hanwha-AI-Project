"""배포 이미지의 폰트 구성 (app/services/render_slides.py 의 LibreOffice 경로).

슬라이드 이미지는 배포 서버에서 LibreOffice 가 굽는다. LibreOffice 는 없는 폰트를
fontconfig 가 고르는 아무 폰트로 바꾸고, 그 폰트의 글자 폭이 원본과 다르면 상자에 맞춰
짜 둔 글이 그대로 줄바꿈된다. 한글 폰트만 깔아 둔 동안 배포에서 '92,929' 가
'92,92 / 9' 로, '2Q25' 가 '2Q2 / 5' 로 쪼개져 나왔다 — 넘친 것은 한글이 아니라 숫자였다.

이 파일은 그 구성을 지운 채 배포되는 것을 막는다. 렌더링 자체는 리눅스 컨테이너에서만
일어나므로 여기서 검사할 수 있는 것은 이미지 설계뿐이다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
DOCKERFILE = BACKEND / "Dockerfile"
FONT_CONF = BACKEND / "fonts-substitutes.conf"

# 이 폰트들이 각각 무엇을 받는지는 Dockerfile 주석에 있다. 하나라도 빠지면 그 폰트를
# 쓰는 런이 폭이 다른 대체본으로 떨어져 슬라이드가 깨진다.
REQUIRED_PACKAGES = [
    "libreoffice-impress",
    "fonts-noto-cjk",  # 맑은 고딕 자리 — 숫자 폭 오차 1~3%
    "fonts-liberation",  # Arial / Times New Roman 과 폭이 같은 대체본
    "fonts-crosextra-carlito",  # Calibri
    "fonts-crosextra-caladea",  # Cambria
]


@pytest.fixture(scope="module")
def dockerfile() -> str:
    if not DOCKERFILE.exists():
        pytest.skip("Dockerfile 이 없습니다.")
    return DOCKERFILE.read_text(encoding="utf-8")


@pytest.mark.parametrize("package", REQUIRED_PACKAGES)
def test_image_installs_the_font_package(dockerfile: str, package: str) -> None:
    assert package in dockerfile, (
        f"'{package}' 가 배포 이미지에서 빠졌습니다. 이유는 Dockerfile 주석에 있습니다 — "
        "폰트를 줄이면 슬라이드의 숫자가 상자를 넘쳐 줄바꿈됩니다."
    )


def test_substitution_rules_are_shipped_into_fontconfig(dockerfile: str) -> None:
    """규칙 파일이 이미지 안 fontconfig 자리에 들어가야 실제로 적용된다."""
    assert FONT_CONF.exists(), "fonts-substitutes.conf 가 없습니다."
    assert "fonts-substitutes.conf" in dockerfile
    assert "/etc/fonts/conf.d/" in dockerfile


def test_korean_windows_fonts_are_mapped_to_noto() -> None:
    """맑은 고딕이 나눔고딕으로 떨어지면 숫자가 11~12% 넓어져 쪼개진다."""
    rules = FONT_CONF.read_text(encoding="utf-8")

    for family in ("Malgun Gothic", "맑은 고딕", "Malgun Gothic Semilight"):
        assert f"<string>{family}</string>" in rules, f"'{family}' 규칙이 없습니다."

    assert "Noto Sans CJK KR" in rules
    # 나눔고딕은 마지막 받침으로만 남는다. 대체 대상으로 적으면 이 버그가 되돌아온다.
    assert "NanumGothic" not in rules and "Nanum Gothic" not in rules
