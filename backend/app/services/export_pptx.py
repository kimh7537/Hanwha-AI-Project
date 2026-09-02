"""SlideDeck -> PPTX 파일 (docs/04-slide-planner.md 의 선택 항목).

이 모듈은 **새로운 문장을 만들지 않는다.** 이미 검증을 마친 `GenerateResponse` 를 그대로
슬라이드 위에 배치할 뿐이다. 여기서 문장을 요약하거나 자르면 원문 근거와의 대응이 깨진다.

python-pptx 가 없어도 앱은 뜬다. JSON / Markdown 다운로드만으로 데모가 성립해야 하므로
(docs/04-slide-planner.md) import 실패는 이 모듈 안에 가둬 두고 API 가 한국어로 안내한다.
"""

from __future__ import annotations

import io

from app.models.contracts import GenerateResponse, Slide
from app.services import labels

try:  # pragma: no cover - 설치 환경에서는 항상 성공한다
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import PP_ALIGN
    from pptx.oxml.ns import qn
    from pptx.oxml.xmlchemy import OxmlElement
    from pptx.util import Inches, Pt

    PPTX_AVAILABLE = True
except ImportError:  # pragma: no cover - 의존성이 빠진 환경
    PPTX_AVAILABLE = False


class PptxUnavailableError(RuntimeError):
    """python-pptx 가 설치되어 있지 않다."""


# 화면(frontend/app/globals.css)의 라이트 테마 색을 그대로 쓴다 --------------
_FOREGROUND = "1B1B1A"
_MUTED = "6B6B66"
_BORDER = "E0E0DC"
_ACCENT = "D1600A"
_ACCENT_SOFT = "FDF1E6"
_WARN = "8A5A00"
_WARN_SOFT = "FDF3E0"
_SURFACE_MUTED = "F1F1EF"

# 한글이 깨지지 않는 폰트. 없는 환경에서는 PowerPoint 가 대체 폰트를 쓴다.
_FONT = "맑은 고딕"

# 16:9
_SLIDE_W = 13.333
_SLIDE_H = 7.5
_MARGIN = 0.7
_CONTENT_W = _SLIDE_W - _MARGIN * 2

_DISCLAIMER = "이 자료는 업로드한 원문을 근거로 생성되었습니다. 발표 전 담당자 검토가 필요합니다."


# --------------------------------------------------------------------------
# 저수준 도우미
# --------------------------------------------------------------------------


def _rgb(hex_value: str) -> "RGBColor":
    return RGBColor.from_string(hex_value)


def _style_run(run, size: float, *, bold: bool = False, color: str = _FOREGROUND) -> None:
    """글꼴을 지정한다.

    python-pptx 의 `font.name` 은 라틴 문자 글꼴(a:latin)만 설정한다. 한글은 동아시아
    글꼴(a:ea)을 따르므로 둘 다 지정해야 PowerPoint 에서 같은 글꼴로 보인다.
    """
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = _rgb(color)
    run.font.name = _FONT

    rPr = run._r.get_or_add_rPr()  # noqa: SLF001 - 동아시아 글꼴은 공개 API 가 없다
    ea = rPr.find(qn("a:ea"))
    if ea is None:
        ea = OxmlElement("a:ea")
        rPr.insert_element_before(
            ea, "a:cs", "a:sym", "a:hlinkClick", "a:hlinkMouseOver", "a:rtl", "a:extLst"
        )
    ea.set("typeface", _FONT)


def _textbox(slide, left: float, top: float, width: float, height: float):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    frame = box.text_frame
    frame.word_wrap = True
    frame.margin_left = 0
    frame.margin_right = 0
    frame.margin_top = 0
    frame.margin_bottom = 0
    return frame


def _line(frame, text: str, size: float, *, first: bool, bold: bool = False,
          color: str = _FOREGROUND, space_after: float = 6, align=None):
    paragraph = frame.paragraphs[0] if first else frame.add_paragraph()
    paragraph.space_after = Pt(space_after)
    if align is not None:
        paragraph.alignment = align
    run = paragraph.add_run()
    run.text = text
    _style_run(run, size, bold=bold, color=color)
    return paragraph


def _rect(slide, left: float, top: float, width: float, height: float, color: str):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = _rgb(color)
    shape.line.fill.background()
    shape.shadow.inherit = False  # 기본 그림자는 업무 자료 톤에 맞지 않는다
    return shape


def _blank(presentation):
    return presentation.slides.add_slide(presentation.slide_layouts[6])


def _body_size(texts: list[str], base: float = 18) -> float:
    """본문 bullet 글자 크기.

    문장을 자르지 않는 것이 원칙이므로(docs/04-slide-planner.md) 넘칠 것 같으면 글자를 줄인다.
    """
    total = sum(len(text) for text in texts)
    if total > 360 or len(texts) > 6:
        return base - 5
    if total > 220:
        return base - 3
    return base


def _shrink(total_chars: int, *, soft: int, hard: int) -> float:
    """부록처럼 글자 크기가 여러 단계인 영역에서 한꺼번에 줄일 폭."""
    if total_chars > hard:
        return 3.5
    if total_chars > soft:
        return 2.0
    return 0.0


# --------------------------------------------------------------------------
# 슬라이드
# --------------------------------------------------------------------------


def _slide_header(slide, title: str, position: str = "") -> None:
    frame = _textbox(slide, _MARGIN, 0.5, _CONTENT_W - 1.7, 0.9)
    _line(frame, title, 28, first=True, bold=True)

    if position:
        marker = _textbox(slide, _SLIDE_W - _MARGIN - 1.6, 0.62, 1.6, 0.35)
        _line(marker, position, 11, first=True, color=_MUTED, align=PP_ALIGN.RIGHT)

    _rect(slide, _MARGIN, 1.45, _CONTENT_W, 0.02, _BORDER)


def _add_title_slide(presentation, result: GenerateResponse) -> None:
    slide = _blank(presentation)
    _rect(slide, 0, 0, 0.22, _SLIDE_H, _ACCENT)

    request = result.request
    frame = _textbox(slide, 1.1, 2.0, 11.2, 1.7)
    _line(frame, result.slide_deck.title or "발표자료", 36, first=True, bold=True)

    meta = " · ".join(
        [
            labels.AUDIENCE_LABELS[request.audience],
            labels.PURPOSE_LABELS[request.purpose],
            f"{request.duration_minutes}분",
            labels.STYLE_LABELS[request.style],
            f"슬라이드 {len(result.slide_deck.slides)}장",
        ]
    )
    meta_frame = _textbox(slide, 1.1, 3.85, 11.2, 0.4)
    _line(meta_frame, meta, 15, first=True, color=_MUTED)

    notices: list[tuple[str, str]] = []
    if request.audience.value == "customer":
        notices.append(("공개 전 검토 필요", "고객용 자료입니다. 내부 정보가 없는지 확인하세요."))
    if result.verification_report is not None:
        report = result.verification_report
        notices.append(
            (
                f"원문 대비 검증: {labels.STATUS_LABELS[report.status]}",
                report.summary,
            )
        )
    if result.meta.fallback_used:
        notices.append(("기본 분석 결과로 대체됨", result.meta.fallback_reason))

    top = 4.45
    for label, detail in notices:
        _rect(slide, 1.1, top, 0.06, 0.5, _ACCENT)
        badge = _textbox(slide, 1.3, top + 0.02, 10.9, 0.5)
        _line(badge, label, 13, first=True, bold=True, color=_WARN, space_after=2)
        if detail:
            _line(badge, detail, 11, first=False, color=_MUTED)
        top += 0.62

    footer = _textbox(slide, 1.1, _SLIDE_H - 1.0, 11.2, 0.5)
    _line(footer, _DISCLAIMER, 11, first=True, color=_MUTED)


def _add_content_slide(
    presentation, slide_data: Slide, index: int, total: int, notes: str
) -> None:
    slide = _blank(presentation)
    _slide_header(slide, slide_data.title or f"슬라이드 {index}", f"{index:02d} / {total:02d}")

    if slide_data.takeaway:
        _rect(slide, _MARGIN, 1.7, _CONTENT_W, 0.78, _ACCENT_SOFT)
        _rect(slide, _MARGIN, 1.7, 0.07, 0.78, _ACCENT)
        frame = _textbox(slide, _MARGIN + 0.25, 1.87, _CONTENT_W - 0.5, 0.5)
        _line(frame, slide_data.takeaway, 15, first=True, bold=True)

    body_top = 2.75 if slide_data.takeaway else 1.75
    frame = _textbox(slide, _MARGIN + 0.15, body_top, _CONTENT_W - 0.3, 6.15 - body_top)
    size = _body_size(slide_data.bullets)
    for order, bullet in enumerate(slide_data.bullets):
        paragraph = _line(frame, f"·  {bullet}", size, first=order == 0, space_after=10)
        paragraph.line_spacing = 1.25

    _rect(slide, _MARGIN, 6.3, _CONTENT_W, 0.02, _BORDER)
    footer = _textbox(slide, _MARGIN, 6.45, _CONTENT_W, 0.7)
    _line(
        footer,
        f"추천 시각자료: {slide_data.visual_suggestion or '없음'}",
        10.5,
        first=True,
        color=_MUTED,
        space_after=3,
    )
    _line(
        footer,
        f"원문 근거: {', '.join(slide_data.source_refs) or '없음'}",
        10.5,
        first=False,
        color=_MUTED,
    )

    if notes:
        slide.notes_slide.notes_text_frame.text = notes


def _add_qa_slides(presentation, result: GenerateResponse) -> None:
    qa = result.presentation_support.qa
    if not qa:
        return

    per_slide = 3
    pages = [qa[start : start + per_slide] for start in range(0, len(qa), per_slide)]
    for page_index, page in enumerate(pages, start=1):
        slide = _blank(presentation)
        position = f"{page_index} / {len(pages)}" if len(pages) > 1 else ""
        _slide_header(slide, "부록 · 예상 질문과 답변", position)

        frame = _textbox(slide, _MARGIN, 1.75, _CONTENT_W, 4.4)
        drop = _shrink(
            sum(len(item.question) + len(item.answer) for item in page), soft=380, hard=560
        )
        first = True
        for item in page:
            _line(frame, f"Q. {item.question}", 15 - drop, first=first, bold=True, space_after=4)
            first = False
            _line(frame, f"A. {item.answer}", 13 - drop, first=False, space_after=3)
            _line(
                frame,
                f"원문 근거: {', '.join(item.source_refs) or '없음'}",
                10.5 - drop / 2,
                first=False,
                color=_MUTED,
                space_after=14,
            )


def _add_verification_slide(presentation, result: GenerateResponse) -> None:
    report = result.verification_report
    if report is None:
        return

    slide = _blank(presentation)
    _slide_header(slide, "부록 · 원문 대비 검증")

    _rect(slide, _MARGIN, 1.7, _CONTENT_W, 0.85, _SURFACE_MUTED)
    head = _textbox(slide, _MARGIN + 0.25, 1.87, _CONTENT_W - 0.5, 0.6)
    _line(
        head,
        f"상태: {labels.STATUS_LABELS[report.status]} · 슬라이드 {report.checked_slides}장 대조",
        14,
        first=True,
        bold=True,
        space_after=3,
    )
    _line(head, report.summary, 11, first=False, color=_MUTED)

    frame = _textbox(slide, _MARGIN + 0.15, 2.8, _CONTENT_W - 0.3, 3.3)
    if not report.items:
        _line(frame, "·  원문과 어긋나는 내용을 찾지 못했습니다.", 14, first=True)
    else:
        shown = report.items[:6]
        drop = _shrink(
            sum(len(item.message) + len(item.suggested_fix) for item in shown),
            soft=420,
            hard=620,
        )
        for order, item in enumerate(shown):
            head_text = (
                f"·  [{labels.SEVERITY_LABELS[item.severity]}] "
                f"{labels.ISSUE_TYPE_LABELS[item.type]}"
            )
            if item.slide_id:
                head_text += f" ({item.slide_id})"
            _line(frame, f"{head_text}: {item.message}", 13 - drop, first=order == 0, space_after=3)
            _line(
                frame,
                f"    수정 제안: {item.suggested_fix}",
                11 - drop / 2,
                first=False,
                color=_MUTED,
                space_after=10,
            )
        if len(report.items) > len(shown):
            _line(
                frame,
                f"·  이 밖에 {len(report.items) - len(shown)}건이 더 있습니다. 화면의 검증 탭에서 확인하세요.",
                11,
                first=False,
                color=_MUTED,
            )

    _rect(slide, _MARGIN, 6.3, _CONTENT_W, 0.02, _BORDER)
    footer = _textbox(slide, _MARGIN, 6.45, _CONTENT_W, 0.6)
    _line(
        footer,
        "이 검증은 확인이 필요한 지점을 알려 줄 뿐 사람 검토를 대체하지 않습니다.",
        10.5,
        first=True,
        color=_MUTED,
    )


def _speaker_notes(result: GenerateResponse, slide_data: Slide) -> str:
    """발표자 노트. 모듈 D 의 스크립트가 있으면 그것을 쓴다."""
    script = next(
        (item for item in result.presentation_support.scripts if item.slide_id == slide_data.id),
        None,
    )
    if script is None:
        return slide_data.speaker_notes

    parts = [f"[약 {script.duration_seconds}초]", script.script]
    if script.must_say:
        parts.append(f"꼭 말할 것: {script.must_say}")
    if slide_data.source_refs:
        parts.append(f"원문 근거: {', '.join(slide_data.source_refs)}")
    return "\n\n".join(part for part in parts if part)


# --------------------------------------------------------------------------
# 진입점
# --------------------------------------------------------------------------


def build_pptx(result: GenerateResponse) -> bytes:
    """생성 결과를 PPTX 바이트로 만든다.

    표지 → 슬라이드 → 부록(예상 Q&A, 검증) 순이며, 발표자 노트에는 모듈 D 의 스크립트가 들어간다.
    """
    if not PPTX_AVAILABLE:
        raise PptxUnavailableError(
            "PPTX 변환 모듈(python-pptx)이 설치되어 있지 않습니다. "
            "Markdown 또는 JSON 다운로드를 이용하세요."
        )

    presentation = Presentation()
    presentation.slide_width = Inches(_SLIDE_W)
    presentation.slide_height = Inches(_SLIDE_H)

    _add_title_slide(presentation, result)

    slides = result.slide_deck.slides
    for index, slide_data in enumerate(slides, start=1):
        _add_content_slide(
            presentation, slide_data, index, len(slides), _speaker_notes(result, slide_data)
        )

    _add_qa_slides(presentation, result)
    _add_verification_slide(presentation, result)

    buffer = io.BytesIO()
    presentation.save(buffer)
    return buffer.getvalue()


def filename_for(result: GenerateResponse) -> str:
    """다운로드 파일명. 파일명에 못 쓰는 문자만 걸러 낸다."""
    title = result.slide_deck.title or result.presentation_id
    cleaned = "".join(" " if char in '\\/:*?"<>|\n\r\t' else char for char in title).strip()
    cleaned = " ".join(cleaned.split())
    return f"{cleaned or result.presentation_id}.pptx"
