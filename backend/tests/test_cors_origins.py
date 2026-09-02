"""배포한 화면이 백엔드를 부를 수 있는지는 CORS 출처 목록 하나에 달려 있다.

여기가 틀리면 화면에는 "백엔드 서버에 연결할 수 없습니다"만 뜨고 원인은 콘솔에만 남는다.
"""

from __future__ import annotations

from app.config import LOCAL_ORIGINS, Settings


def _origins(value: str) -> list[str]:
    return Settings(extra_origins=value).allowed_origins


def test_로컬_주소는_설정이_없어도_허용된다():
    assert _origins("") == list(LOCAL_ORIGINS)


def test_배포_주소를_쉼표로_여러_개_받는다():
    origins = _origins("https://a.vercel.app, https://b.example.com")
    assert origins[-2:] == ["https://a.vercel.app", "https://b.example.com"]


def test_끝의_슬래시와_빈_항목을_떼어_낸다():
    # 브라우저의 Origin 에는 끝 슬래시가 없다. 붙은 채로 두면 글자 대조에서 어긋난다.
    assert _origins("https://a.vercel.app/, ,")[-1:] == ["https://a.vercel.app"]
