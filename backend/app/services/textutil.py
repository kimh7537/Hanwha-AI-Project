"""모듈 A~E 가 공유하는 한국어 텍스트 유틸.

여기 있는 함수는 전부 결정론적이다. LLM 없이도 파이프라인이 끝까지 돌아가야 하기 때문이다.
"""

from __future__ import annotations

import re

# 숫자 + 단위. 검증 모듈의 숫자 대조와 분석 모듈의 수치 추출이 같은 정의를 쓴다.
NUMBER_PATTERN = re.compile(
    r"(?P<value>\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)"
    r"\s*(?P<unit>%p|%|퍼센트|배|초|분|시간|일|주|개월|년|건|개|명|자|점|원|만원|억원|억|만|"
    r"ms|GB|MB|KB|TB)?"
)

# 날짜 표기의 단위. 발표에서 인용할 "수치"가 아니므로 수치 추출에서 제외한다.
_DATE_UNITS = {"년", "일"}

SENTENCE_END = re.compile(r"(?<=[.!?])\s+|(?<=다\.)\s*|(?<=요\.)\s*|\n+")

BULLET_PREFIX = re.compile(r"^\s*(?:[-*•·]|\d+[.)]|[가-힣][.)])\s+")

# 반드시 유지해야 하는 조건/주의사항을 나타내는 표지.
# 값이 클수록 "발표에서 빠지면 안 되는 강한 조건"이다 (must_keep 정렬에 사용).
CONDITION_WEIGHTS: dict[str, int] = {
    "금지": 5, "반드시": 5, "해야 한다": 4, "해야만": 4, "필수": 4, "전제": 4,
    "주의": 3, "제한": 3, "승인": 3, "확정되지": 3, "한한": 3,
    "우선한다": 2, "단,": 2, "다만": 2,
    "이상": 1, "미만": 1, "초과": 1, "이하": 1,
}

CONDITION_MARKERS = tuple(CONDITION_WEIGHTS)


def condition_strength(text: str) -> int:
    """조건 문장의 강도. 0이면 조건이 아니다."""
    lowered = (text or "").lower()
    return sum(weight for marker, weight in CONDITION_WEIGHTS.items() if marker.lower() in lowered)

# 도입 효과를 나타내는 표지. 값이 클수록 실제 성과 서술에 가깝다.
# ("개선폭이 0.4%p 미만" 같은 실험 세부보다 "3분 20초에서 25초로 줄었다" 를 앞세우기 위함)
EFFECT_WEIGHTS: dict[str, int] = {
    "줄었": 5, "감소": 5, "단축": 5, "절감": 5,
    "향상": 3, "증가": 3,
    "효과": 2, "개선": 1,
}


def effect_strength(text: str) -> int:
    """도입 효과 서술로서의 강도. 0이면 효과 문장이 아니다."""
    lowered = (text or "").lower()
    return sum(weight for marker, weight in EFFECT_WEIGHTS.items() if marker.lower() in lowered)


# 고객용 자료에서 걸러야 하는 내부 정보 표지
INTERNAL_MARKERS = (
    "사내", "내부", "대외비", "기밀", "전사", "정보시스템팀", "정보보호팀", "파트",
    "본부", "팀 대상", "K-Drive",
)

# 원문 근거 없이 쓰면 안 되는 과장 표현
EXAGGERATION_MARKERS = ("최고", "완벽", "무조건", "100%", "절대", "유일한", "혁신적")

_STOPWORDS = {
    "그리고", "그러나", "하지만", "또한", "이는", "있다", "없다", "한다", "된다",
    "위해", "통해", "대한", "관련", "경우", "이후", "다음", "같은", "가장", "매우",
}


def normalize(text: str) -> str:
    """비교용 정규화: 공백을 접고 좌우를 자른다."""
    return re.sub(r"\s+", " ", text or "").strip()


def split_sentences(text: str) -> list[str]:
    """한국어 문서를 문장 단위로 자른다.

    원문은 하드 줄바꿈으로 감겨 있는 경우가 많다. 줄 단위로 자르면 문장이 조각나므로,
    같은 문단의 연속된 줄을 먼저 이어 붙인 뒤 문장 경계로 자른다.
    불릿 줄은 그 자체로 한 문장으로 취급한다.
    """
    sentences: list[str] = []
    pending: list[str] = []

    def flush_pending() -> None:
        if not pending:
            return
        merged = " ".join(pending)
        pending.clear()
        for part in SENTENCE_END.split(merged):
            cleaned = normalize(part)
            if cleaned:
                sentences.append(cleaned)

    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            flush_pending()
            continue
        if BULLET_PREFIX.match(line):
            # 새 불릿이 시작되면 이전 문단/불릿을 마감한다.
            # 불릿의 이어지는 줄은 pending 에 계속 쌓여 하나의 문장으로 합쳐진다.
            flush_pending()
            pending.append(normalize(BULLET_PREFIX.sub("", line)))
            continue
        pending.append(line)

    flush_pending()
    return [s for s in sentences if len(s) >= 6]


def is_bullet_line(line: str) -> bool:
    return bool(BULLET_PREFIX.match(line or ""))


def iter_bullets(text: str) -> list[str]:
    """불릿 항목 본문 목록. 여러 줄에 걸친 불릿은 하나로 이어 붙인다."""
    bullets: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            bullets.append(normalize(" ".join(current)))
            current.clear()

    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            flush()
            continue
        if BULLET_PREFIX.match(line):
            flush()
            current.append(BULLET_PREFIX.sub("", line))
        elif current:
            # 들여쓴 이어지는 줄
            current.append(line)

    flush()
    return [b for b in bullets if len(b) >= 8]


def extract_numbers(text: str) -> list[tuple[str, str]]:
    """발표에서 인용할 만한 (값, 단위) 목록.

    목차 번호("1. 배경"), 버전("v2.1"), 날짜("2026년 7월 14일")는 수치가 아니므로 제외한다.
    단위가 없는 값은 0.91, 0.6 같은 점수/비율만 남긴다.
    """
    source = text or ""
    found: list[tuple[str, str]] = []

    for match in NUMBER_PATTERN.finditer(source):
        value = match.group("value")
        unit = match.group("unit") or ""

        if unit in _DATE_UNITS:
            continue

        # 앞 문자가 영문자면 식별자의 일부다 (v2.1 의 버전, F1 의 지표 이름)
        # 앞 문자가 소수점이면 버전 문자열의 일부다 (1.0.3)
        prefix = source[max(0, match.start() - 1) : match.start()]
        if prefix == "." or prefix.isascii() and prefix.isalpha():
            continue

        if not unit:
            # 단위 없는 값은 0.xx 형태의 점수/신뢰도만 인정한다
            if not value.startswith("0."):
                continue

        found.append((value, unit))

    return found


def number_key(value: str) -> str:
    """숫자 대조용 키. 자릿수 구분 쉼표와 소수점 뒤 0 을 무시한다."""
    digits = (value or "").replace(",", "").strip()
    if digits.endswith(".0"):
        digits = digits[:-2]
    return digits


def tokenize(text: str) -> list[str]:
    """한국어/영문 혼용 문서용 러프 토크나이저. 검색과 중복 판정에 쓴다."""
    tokens = re.findall(r"[A-Za-z]{2,}|[가-힣]{2,}|\d+(?:\.\d+)?", text or "")
    return [t for t in tokens if t not in _STOPWORDS]


def keyword_overlap(text: str, keywords: list[str]) -> int:
    """텍스트가 포함한 키워드 개수."""
    lowered = (text or "").lower()
    return sum(1 for kw in keywords if kw and kw.lower() in lowered)


def contains_any(text: str, markers: tuple[str, ...] | list[str]) -> list[str]:
    lowered = (text or "").lower()
    return [m for m in markers if m.lower() in lowered]


def shorten(text: str, limit: int) -> str:
    """길이 제한. 문장 중간이면 말줄임표를 붙인다. (근거 미리보기용)"""
    cleaned = normalize(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 1)].rstrip() + "…"


def clip_clause(text: str, limit: int) -> str:
    """말줄임표 없이 절 경계에서 자른다.

    슬라이드 제목·takeaway·스크립트처럼 화면에 그대로 읽히는 문장에 쓴다.
    잘린 티가 나는 '…' 는 발표자료에서 결함처럼 보이므로 쓰지 않는다.
    """
    cleaned = normalize(text)
    if len(cleaned) <= limit:
        return cleaned

    window = cleaned[:limit]
    # "~으로", "~이며" 같은 연결 어미에서 자르면 문장이 끊긴 티가 난다. 절 경계만 쓴다.
    for boundary in (", ", " 및 ", "하며 "):
        position = window.rfind(boundary)
        if position > limit * 0.5:
            return window[: position + len(boundary)].strip().rstrip(",")

    position = window.rfind(" ")
    return (window[:position] if position > limit * 0.4 else window).strip().rstrip(",")


def first_sentence(text: str, limit: int = 120) -> str:
    """첫 문장을 온전한 형태로 돌려준다."""
    sentences = split_sentences(text)
    candidate = sentences[0] if sentences else normalize(text)
    return clip_clause(candidate, limit)


def strip_english_gloss(text: str) -> str:
    """원어 유지가 꺼졌을 때 영문 병기를 제거한다.

    '임베딩(embedding, 여러 ~ 방식)' -> '임베딩(여러 ~ 방식)'
    '임베딩(embedding)'              -> '임베딩'

    청중 변환과 Q&A 생성이 같은 규칙을 써야 화면에서 용어 표기가 어긋나지 않는다.
    """
    result = re.sub(r"\(([A-Za-z][A-Za-z0-9 \-]*),\s*([^)]+)\)", r"(\2)", text or "")
    return re.sub(r"\s*\([A-Za-z][A-Za-z0-9 \-]*\)", "", result)


def to_bullet(text: str, limit: int = 90) -> str:
    """슬라이드 bullet 용 문장 정리.

    개조식(명사형 종결)으로 바꾸려면 형태소 분석이 필요하다. 규칙만으로 어미를 떼면
    "줄었다" -> "줄었" 처럼 망가지므로, 서술 어미는 그대로 두고 접속어와 마침표만 정리한다.
    화면에 그대로 읽히므로 말줄임표 대신 절 경계에서 자른다.
    """
    cleaned = normalize(text)
    cleaned = re.sub(r"^(?:또한|그리고|하지만|그러나|다만|단,)\s*", "", cleaned)
    cleaned = cleaned.rstrip(".")
    return clip_clause(cleaned, limit)
