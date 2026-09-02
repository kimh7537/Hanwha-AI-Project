"""모듈 E: 원문 대비 검증 -> VerificationReport (docs/06-verification.md).

핵심 차별화 기능이자 평가표의 "적합한 AI 툴 선택" 근거다.
근거·숫자 검사는 전부 결정론적 규칙 로직으로 구현한다. LLM 에 판정을 떠넘기지 않는다.
근거 없는 신뢰도 점수는 만들지 않는다.
"""

from __future__ import annotations

from app.models.contracts import (
    Audience,
    IssueType,
    PresentationRequest,
    PresentationSupport,
    ReportStatus,
    Severity,
    Slide,
    SlideDeck,
    SourceAnalysis,
    VerificationItem,
    VerificationReport,
)
from app.services import textutil

STAGE = "정확성 검증"

# 원문의 수치가 조건부로 한정되어 있음을 알려주는 표지
_QUALIFIER_MARKERS = ("한한", "한하여", "단,", "다만", "경우", "미만", "이상", "초과", "이하", "전제")


def _slide_text(slide: Slide) -> str:
    return " ".join([slide.title, slide.takeaway, *slide.bullets])


def _deck_text(deck: SlideDeck) -> str:
    return " ".join(_slide_text(slide) for slide in deck.slides)


def _source_number_keys(analysis: SourceAnalysis) -> set[str]:
    keys: set[str] = set()
    for evidence in analysis.source_evidence:
        for value, _unit in textutil.extract_numbers(evidence.text):
            keys.add(textutil.number_key(value))
    return keys


def _check_evidence(deck: SlideDeck, analysis: SourceAnalysis) -> list[VerificationItem]:
    """1) 원문에 없는 주장 — 근거가 없거나 존재하지 않는 chunk 를 가리키는 슬라이드."""
    known = {e.id for e in analysis.source_evidence}
    items: list[VerificationItem] = []

    for slide in deck.slides:
        if not slide.source_refs:
            items.append(
                VerificationItem(
                    severity=Severity.CRITICAL,
                    slide_id=slide.id,
                    type=IssueType.UNSUPPORTED_CLAIM,
                    message=f"'{slide.title}' 슬라이드에 원문 근거가 없습니다.",
                    source_refs=[],
                    suggested_fix="이 슬라이드의 내용을 뒷받침하는 원문 chunk 를 연결하거나 슬라이드를 삭제하세요.",
                )
            )
            continue

        unknown = [ref for ref in slide.source_refs if ref not in known]
        if unknown:
            items.append(
                VerificationItem(
                    severity=Severity.CRITICAL,
                    slide_id=slide.id,
                    type=IssueType.UNSUPPORTED_CLAIM,
                    message=(
                        f"'{slide.title}' 슬라이드가 존재하지 않는 근거를 가리킵니다: "
                        + ", ".join(unknown)
                    ),
                    source_refs=[],
                    suggested_fix="유효한 chunk id 로 근거를 다시 연결하세요.",
                )
            )
    return items


def _check_numbers(
    deck: SlideDeck, support: PresentationSupport, analysis: SourceAnalysis
) -> list[VerificationItem]:
    """2) 숫자·단위 오류 — 원문에 없는 숫자가 자료에 등장하는지."""
    source_keys = _source_number_keys(analysis)
    items: list[VerificationItem] = []
    reported: set[tuple[str, str]] = set()

    def scan(slide_id: str, label: str, text: str) -> None:
        for value, unit in textutil.extract_numbers(text):
            key = textutil.number_key(value)
            if key in source_keys:
                continue
            if (slide_id, key) in reported:
                continue
            reported.add((slide_id, key))
            items.append(
                VerificationItem(
                    severity=Severity.CRITICAL,
                    slide_id=slide_id,
                    type=IssueType.NUMBER_ERROR,
                    message=f"{label}에 원문에서 확인되지 않는 숫자 '{value}{unit}' 가 있습니다.",
                    source_refs=[],
                    suggested_fix="원문에 있는 값으로 수정하거나, 근거를 찾지 못하면 해당 수치를 삭제하세요.",
                )
            )

    for slide in deck.slides:
        scan(slide.id, f"'{slide.title}' 슬라이드", _slide_text(slide))
    for script in support.scripts:
        scan(script.slide_id, "발표 스크립트", script.script)

    return items


def _qualified_number_tokens(analysis: SourceAnalysis) -> dict[str, tuple[str, str]]:
    """원문에서 조건이 붙어 등장하는 수치 토큰 -> (그 조건 문장, chunk id).

    같은 값이 여러 번 나오는 문서에서는 SourceAnalysis.numbers 의 meaning 이 조건이 없는
    쪽 문장일 수 있다. 그래서 요약이 아니라 원문 문장을 직접 훑는다.
    """
    tokens: dict[str, tuple[str, str]] = {}
    for evidence in analysis.source_evidence:
        for sentence in textutil.split_sentences(evidence.text):
            if not textutil.contains_any(sentence, _QUALIFIER_MARKERS):
                continue
            for value, unit in textutil.extract_numbers(sentence):
                # 단위까지 포함한 토큰으로만 판정한다.
                # 값만 비교하면 "3만 건"의 3 이 "3개 부서"의 3 과 겹쳐 오탐이 난다.
                tokens.setdefault(f"{value}{unit}", (sentence, evidence.id))
    return tokens


def _check_distortion(deck: SlideDeck, analysis: SourceAnalysis) -> list[VerificationItem]:
    """3) 의미 왜곡 — 원문에서 조건부로 한정된 수치를 조건 없이 인용한 경우."""
    qualified = _qualified_number_tokens(analysis)
    if not qualified:
        return []

    items: list[VerificationItem] = []
    for slide in deck.slides:
        text = _slide_text(slide)
        if textutil.contains_any(text, _QUALIFIER_MARKERS):
            continue  # 슬라이드가 조건을 함께 언급하고 있다

        for token, (sentence, evidence_id) in qualified.items():
            if token not in text:
                continue
            items.append(
                VerificationItem(
                    severity=Severity.WARNING,
                    slide_id=slide.id,
                    type=IssueType.DISTORTION,
                    message=(
                        f"'{token}' 는 원문에서 조건이 붙은 수치입니다: "
                        f"{textutil.shorten(sentence, 70)} "
                        "슬라이드에는 조건 없이 인용되어 단정처럼 읽힙니다."
                    ),
                    source_refs=[evidence_id],
                    suggested_fix="수치에 적용되는 조건을 bullet 에 함께 표기하세요.",
                )
            )
    return items


def _check_must_keep(deck: SlideDeck, analysis: SourceAnalysis) -> list[VerificationItem]:
    """4) 과도한 단순화 — 반드시 유지해야 할 조건이 덱에 반영되지 않은 경우."""
    if not analysis.must_keep:
        return []

    deck_tokens = set(textutil.tokenize(_deck_text(deck)))
    items: list[VerificationItem] = []

    for condition in analysis.must_keep:
        tokens = [t for t in textutil.tokenize(condition.text) if len(t) >= 2]
        if not tokens:
            continue
        hit = sum(1 for token in tokens if token in deck_tokens)
        if hit / len(tokens) >= 0.5:
            continue  # 절반 이상 반영되어 있으면 통과로 본다
        items.append(
            VerificationItem(
                severity=Severity.WARNING,
                slide_id="",
                type=IssueType.OVERSIMPLIFICATION,
                message=(
                    "원문의 조건이 발표자료에 반영되지 않았습니다: "
                    + textutil.shorten(condition.text, 70)
                ),
                source_refs=list(condition.source_refs),
                suggested_fix="이 조건을 관련 슬라이드의 bullet 으로 추가하세요.",
            )
        )
    return items[:3]  # 조건이 많은 문서에서 리포트가 조건 목록으로 뒤덮이지 않게 상위 3건만


def _check_keywords(deck: SlideDeck, request: PresentationRequest) -> list[VerificationItem]:
    """5) 핵심 내용 누락 — 필수 키워드가 덱에 등장하지 않는 경우."""
    text = _deck_text(deck)
    items: list[VerificationItem] = []
    for keyword in request.keywords:
        if keyword and keyword not in text:
            items.append(
                VerificationItem(
                    severity=Severity.WARNING,
                    slide_id="",
                    type=IssueType.OMISSION,
                    message=f"필수 키워드 '{keyword}' 가 발표자료에 등장하지 않습니다.",
                    source_refs=[],
                    suggested_fix=f"'{keyword}' 를 다루는 내용이 원문에 있는지 확인하고 슬라이드에 반영하세요.",
                )
            )
    return items


def _check_sensitive(
    deck: SlideDeck, support: PresentationSupport, request: PresentationRequest
) -> list[VerificationItem]:
    """6) 고객용 자료의 민감·내부 정보 위험."""
    if request.audience is not Audience.CUSTOMER:
        return []

    items: list[VerificationItem] = []
    script_by_slide = {script.slide_id: script.script for script in support.scripts}

    for slide in deck.slides:
        # 슬라이드뿐 아니라 발표 스크립트도 검사한다. 발표자가 실제로 입 밖에 내는 문장이기 때문.
        text = _slide_text(slide) + " " + script_by_slide.get(slide.id, "")
        internal = textutil.contains_any(text, textutil.INTERNAL_MARKERS)
        if internal:
            items.append(
                VerificationItem(
                    severity=Severity.WARNING,
                    slide_id=slide.id,
                    type=IssueType.SENSITIVE_INFO,
                    message=(
                        "고객용 자료에 내부 정보로 보이는 표현이 있습니다: "
                        + ", ".join(sorted(set(internal)))
                    ),
                    source_refs=list(slide.source_refs),
                    suggested_fix="내부 조직명·시스템명을 일반 명칭으로 바꾸거나 공개 승인 여부를 확인하세요.",
                )
            )

        exaggeration = textutil.contains_any(text, textutil.EXAGGERATION_MARKERS)
        if exaggeration:
            items.append(
                VerificationItem(
                    severity=Severity.WARNING,
                    slide_id=slide.id,
                    type=IssueType.SENSITIVE_INFO,
                    message="과장으로 읽힐 수 있는 표현이 있습니다: " + ", ".join(sorted(set(exaggeration))),
                    source_refs=list(slide.source_refs),
                    suggested_fix="원문 근거로 뒷받침되는 표현으로 바꾸세요.",
                )
            )

    return items


def _summarize(items: list[VerificationItem], deck: SlideDeck) -> tuple[ReportStatus, str]:
    critical = [i for i in items if i.severity is Severity.CRITICAL]
    warning = [i for i in items if i.severity is Severity.WARNING]

    if critical:
        return (
            ReportStatus.REVIEW_NEEDED,
            f"원문과 어긋나거나 근거가 없는 내용이 {len(critical)}건 있어 수정이 필요합니다.",
        )
    if warning:
        return (
            ReportStatus.WARNING,
            f"발표 전에 확인이 필요한 문장이 {len(warning)}건 있습니다.",
        )
    return (
        ReportStatus.OK,
        f"슬라이드 {len(deck.slides)}장 모두 원문 근거와 연결되어 있으며 어긋나는 내용을 찾지 못했습니다.",
    )


def verify(
    deck: SlideDeck,
    support: PresentationSupport,
    analysis: SourceAnalysis,
    request: PresentationRequest,
) -> VerificationReport:
    """모듈 E 진입점. 전부 규칙 기반이므로 LLM 없이도 항상 같은 결과를 낸다."""
    items: list[VerificationItem] = []
    items.extend(_check_evidence(deck, analysis))
    items.extend(_check_numbers(deck, support, analysis))
    items.extend(_check_distortion(deck, analysis))
    items.extend(_check_must_keep(deck, analysis))
    items.extend(_check_keywords(deck, request))
    items.extend(_check_sensitive(deck, support, request))

    severity_order = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.INFO: 2}
    items.sort(key=lambda item: (severity_order[item.severity], item.slide_id))

    status, summary = _summarize(items, deck)
    return VerificationReport(
        summary=summary,
        status=status,
        items=items,
        checked_slides=len(deck.slides),
    )
