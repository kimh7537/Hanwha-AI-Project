"""PPTX 를 슬라이드 이미지(PNG)로 굽는다 — 화면의 원본/결과 대조에 쓴다.

굽는 방법이 둘이다. 윈도우에서는 설치된 PowerPoint 를 COM 으로 부린다 — 사내 PC 에
LibreOffice 는 없고 PowerPoint 는 있으며, 표·도형·배경·글꼴이 원본 그대로 나온다.
배포한 리눅스 컨테이너에는 PowerPoint 가 없으므로 LibreOffice 로 굽는다. 둘 다 없으면
`available()` 이 False 를 돌려주고 화면은 글자 대조로 되돌아간다 — 렌더링이 없다고
데모가 멈추면 안 된다(docs/10-quality-safety.md).
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import threading
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path

_log = logging.getLogger(__name__)

# 발표 화면에서 좌우로 반씩 쓰므로 1280x720 이면 충분하다.
WIDTH = 1280
HEIGHT = 720

# LibreOffice 는 컨테이너가 막 뜬 첫 변환에서 30초 가까이 걸린다. 그보다 오래 걸리면
# 매달려 있는 것이므로 끊고 화면을 글자 대조로 돌려보낸다.
_SOFFICE_TIMEOUT_SECONDS = 180

# PowerPoint 는 한 번에 한 덱만 굽는다. 요청이 겹치면 줄을 세운다.
# ponytail: 렌더 내내 락을 쥔다. 첫 요청이 8초쯤 걸리고 그 뒤로는 캐시라 데모에는 충분하다.
_LOCK = threading.Lock()

# ponytail: 최근 4덱만 메모리에 둔다. 더 필요하면 디스크 캐시로 옮긴다.
_CACHE: OrderedDict[str, list[bytes]] = OrderedDict()
_CACHE_MAX = 4

_available: bool | None = None


def available() -> bool:
    """슬라이드 이미지를 만들 수 있는 환경인지.

    PowerPoint 를 먼저 본다. 둘 다 있는 PC 라면 원본에 더 가깝게 나오는 쪽이 그쪽이다.
    """
    return _powerpoint_available() or _soffice() is not None


def _powerpoint_available() -> bool:
    """이 PC 에서 PowerPoint 렌더링이 가능한지. 한 번만 확인하고 기억한다."""
    global _available
    if _available is None:
        _available = _probe()
    return _available


@lru_cache(maxsize=1)
def _soffice() -> str | None:
    """LibreOffice 실행 파일 경로. 배포한 리눅스 컨테이너에는 이쪽만 있다."""
    return shutil.which("soffice") or shutil.which("libreoffice")


def _probe() -> bool:
    """PowerPoint 를 띄우지 않고 등록 여부만 본다 (헬스체크가 앱을 실행하면 안 된다).

    레지스트리의 ProgID 만 읽는다. COM 을 열면 확인하는 것만으로 PowerPoint 가 뜬다.
    """
    try:
        import win32com.client  # noqa: F401, PLC0415 - 윈도우에서만 있는 선택적 의존성
    except ImportError:
        return False

    try:
        import winreg  # noqa: PLC0415 - 윈도우 전용

        with winreg.OpenKey(
            winreg.HKEY_CLASSES_ROOT, r"PowerPoint.Application\CLSID"
        ):
            pass
    except Exception:  # noqa: BLE001 - 설치 상태는 통제 밖이다
        _log.info("PowerPoint 를 찾지 못해 슬라이드 렌더링을 끕니다", exc_info=True)
        return False
    return True


def render(key: str, data: bytes) -> list[bytes]:
    """PPTX 바이트를 슬라이드 순서대로 PNG 로 만든다. 같은 key 는 한 번만 굽는다."""
    with _LOCK:
        cached = _CACHE.get(key)
        if cached is not None:
            _CACHE.move_to_end(key)
            return cached

        images = (
            _render_with_powerpoint(data)
            if _powerpoint_available()
            else _render_with_soffice(data)
        )
        _CACHE[key] = images
        while len(_CACHE) > _CACHE_MAX:
            _CACHE.popitem(last=False)
        return images


def _render_with_powerpoint(data: bytes) -> list[bytes]:
    import pythoncom  # noqa: PLC0415 - 윈도우에서만 있는 선택적 의존성
    import win32com.client  # noqa: PLC0415

    pythoncom.CoInitialize()
    app = None
    presentation = None
    try:
        with tempfile.TemporaryDirectory() as work:
            source = Path(work) / "deck.pptx"
            source.write_bytes(data)

            # DispatchEx 로 우리 인스턴스를 새로 띄운다. Dispatch 는 사용자가 열어 둔
            # PowerPoint 에 붙어서, 아래 Quit 이 그 사람 작업까지 닫아버린다.
            app = win32com.client.DispatchEx("PowerPoint.Application")
            presentation = app.Presentations.Open(
                str(source), ReadOnly=1, Untitled=0, WithWindow=0
            )

            images: list[bytes] = []
            for index in range(1, presentation.Slides.Count + 1):
                target = Path(work) / f"slide-{index}.png"
                presentation.Slides(index).Export(str(target), "PNG", WIDTH, HEIGHT)
                images.append(target.read_bytes())
            return images
    finally:
        for close in (
            lambda: presentation.Close() if presentation is not None else None,
            lambda: app.Quit() if app is not None else None,
            pythoncom.CoUninitialize,
        ):
            try:
                close()
            except Exception:  # noqa: BLE001 - 정리 실패로 요청을 깨뜨리지 않는다
                _log.warning("PowerPoint 정리 중 오류", exc_info=True)


def _render_with_soffice(data: bytes) -> list[bytes]:
    """LibreOffice 로 PDF 를 한 번 거쳐 PNG 로 굽는다 — PowerPoint 가 없는 배포 서버용.

    PDF 를 거치는 이유: `--convert-to png` 는 첫 장만 내보낸다. 낱장으로 받으려면
    PDF 로 바꾼 뒤 쪽마다 그리는 수밖에 없고, 그 일은 이미 의존성인 PyMuPDF 가 한다.
    """
    soffice = _soffice()
    if soffice is None:
        raise RuntimeError("LibreOffice(soffice) 를 찾지 못했습니다.")

    with tempfile.TemporaryDirectory() as work:
        source = Path(work) / "deck.pptx"
        source.write_bytes(data)

        completed = subprocess.run(
            [
                soffice,
                "--headless",
                "--norestore",
                # 프로필을 임시 디렉터리에 새로 만든다. 기본 프로필은 홈이 읽기 전용이거나
                # 이전 실행이 남긴 잠금 파일이 있으면 조용히 실패한다.
                f"-env:UserInstallation=file://{Path(work).as_posix()}/profile",
                "--convert-to",
                "pdf",
                "--outdir",
                work,
                str(source),
            ],
            capture_output=True,
            timeout=_SOFFICE_TIMEOUT_SECONDS,
            check=False,
        )

        pdf = Path(work) / "deck.pdf"
        if not pdf.exists():
            # soffice 는 변환에 실패해도 종료 코드 0 을 주는 일이 있어 파일로 판단한다.
            raise RuntimeError(
                "LibreOffice 가 PPTX 를 PDF 로 바꾸지 못했습니다: "
                f"{completed.stderr.decode('utf-8', 'replace')[:200]}"
            )

        return _pdf_to_pngs(pdf)


def _pdf_to_pngs(pdf: Path) -> list[bytes]:
    """PDF 의 각 쪽을 WIDTH×HEIGHT PNG 로 그린다.

    쪽 비율을 지키지 않고 상자에 맞춘다. PowerPoint 경로의 `Export(width, height)` 가
    그렇게 동작하고, 두 경로가 같은 좌표계를 내야 화면의 변경 표시 네모가 양쪽에 맞는다.
    """
    import fitz  # noqa: PLC0415 - pymupdf. 렌더링할 때만 필요하다

    with fitz.open(pdf) as document:
        return [
            page.get_pixmap(
                matrix=fitz.Matrix(WIDTH / page.rect.width, HEIGHT / page.rect.height)
            ).tobytes("png")
            for page in document
        ]
