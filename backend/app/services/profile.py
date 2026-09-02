"""청중 프로파일과 메시지 통제가 '무엇을 앞으로 당길지'를 정한다.

`Audience` 가 이야기의 뼈대(`audience.AUDIENCE_STORYLINE`)를 정한다면, 여기 규칙은 그 뼈대
안에서 **어떤 사실이 먼저 오고 무엇이 잘려 나가는지**를 정한다. 같은 '고객사'라도 기술
이해도와 관심 축이 다르면 실을 문장이 달라진다.

절대 규칙은 모듈 B 와 같다 — **사실을 만들지도 지우지도 않는다.** 여기서 하는 일은 순위를
올리고 내리는 것뿐이다. 그래서 `minimize` 는 삭제가 아니라 감점이고, `banned` 는 고르는
단계에서 회피하되 남은 것은 검증 리포트가 잡는다(services/verifier.py).
"""

from __future__ import annotations

from app.models.contracts import Interest, PresentationRequest
from app.services import textutil
from app.services.labels import INTEREST_LABELS

# 관심 영역별로 원문에서 찾을 말. 원문 어휘에 맞춰 넓게 잡는다 —
# 못 찾으면 순위가 안 움직일 뿐이라 과하게 잡아도 사실이 왜곡되지 않는다.
INTEREST_KEYWORDS: dict[Interest, tuple[str, ...]] = {
    Interest.TECHNOLOGY: (
        "구조", "아키텍처", "알고리즘", "모델", "구성", "동작", "방식", "엔진",
        "파이프라인", "설계", "기술",
    ),
    Interest.PERFORMANCE: (
        "성능", "속도", "처리", "정확도", "지연", "처리량", "응답", "정확", "품질",
    ),
    Interest.COST: (
        "비용", "원가", "절감", "예산", "인건비", "투자", "효율", "공수",
    ),
    Interest.SAFETY: (
        "안전", "보안", "리스크", "위험", "장애", "오류", "규정", "준수", "감사", "안정",
    ),
    Interest.SCHEDULE: (
        "일정", "기간", "도입", "적용", "단계", "개월", "주차", "시점", "전환",
    ),
}

# 이해도가 용어 풀이 개수를 얼마나 움직이는가. 청중이 정한 기본값에 더한다.
# 낮을수록 풀어 주고, 높을수록 덜어낸다 — 이해도 3 은 청중 기본값 그대로다.
_EXPERTISE_GLOSSARY_DELTA: dict[int, int] = {1: 3, 2: 1, 3: 0, 4: -1, 5: -2}

# 청중 기본이 '전부'(None)일 때, 이해도가 높으면 몇 개로 줄이는가.
_EXPERTISE_CAP_WHEN_ALL: dict[int, int | None] = {1: None, 2: None, 3: None, 4: 2, 5: 0}

# 이해도가 한 항목에 담는 문장 수를 얼마나 움직이는가. 낮으면 더 풀어 쓴다.
_EXPERTISE_DEPTH_DELTA: dict[int, int] = {1: 1, 2: 1, 3: 0, 4: 0, 5: -1}

_INTEREST_BONUS = 2.0
_MUST_CONVEY_BONUS = 3.0
_MINIMIZE_PENALTY = 3.0
_BANNED_PENALTY = 8.0
_KNOWN_PENALTY = 1.5


def resolve_glossary_limit(audience_limit: int | None, expertise: int) -> int | None:
    """청중 기본값에 이해도를 반영한 최종 용어 풀이 개수. None 은 전부.

    임원 기본은 0 이지만 이해도가 낮으면 늘어난다 — 프로파일은 청중을 덮어쓰는 게 아니라
    한 단계 더 좁히는 것이다. 이해도가 높으면 신입이라도 용어 풀이가 줄어든다.
    """
    if audience_limit is None:
        return _EXPERTISE_CAP_WHEN_ALL.get(expertise)
    return max(0, audience_limit + _EXPERTISE_GLOSSARY_DELTA.get(expertise, 0))


def resolve_depth(base: int, expertise: int) -> int:
    """한 항목에 담을 문장 수. 이해도가 낮으면 한 문장 더 풀어 쓴다."""
    return max(1, base + _EXPERTISE_DEPTH_DELTA.get(expertise, 0))


def interest_terms(request: PresentationRequest) -> list[str]:
    """선택한 관심 영역이 원문에서 찾을 말들."""
    terms: list[str] = []
    for interest in request.profile.interests:
        terms.extend(INTEREST_KEYWORDS.get(interest, ()))
    return terms


def rank_score(text: str, request: PresentationRequest) -> float:
    """이 문장이 이번 발표에서 얼마나 앞에 와야 하는가.

    0 은 '중립'이고 음수도 나온다. 점수가 사실을 바꾸지는 않는다 — 같은 항목 안에서 순서만
    바꾸고, 분량이 모자라 잘릴 때 무엇이 먼저 빠질지를 정한다.
    """
    if not text:
        return 0.0

    message = request.message
    score = 0.0
    score += _INTEREST_BONUS * textutil.keyword_overlap(text, interest_terms(request))
    score -= _MINIMIZE_PENALTY * textutil.keyword_overlap(text, message.minimize)
    score -= _BANNED_PENALTY * len(textutil.contains_any(text, message.banned))

    if message.must_convey:
        score += _MUST_CONVEY_BONUS * _token_overlap(text, message.must_convey)

    # 이미 아는 내용을 다시 설명하지 않는다. 지우지는 않고 뒤로 민다.
    if request.profile.prior_knowledge:
        score -= _KNOWN_PENALTY * _token_overlap(text, request.profile.prior_knowledge)

    return score


def rank(texts: list[str], request: PresentationRequest) -> list[str]:
    """점수 순으로 다시 세운다. 같은 점수면 원문 순서를 지킨다(안정 정렬)."""
    return sort_by_score(list(texts), request, lambda text: text)


def sort_by_score(items: list, request: PresentationRequest, text_of) -> list:
    """`rank` 와 같은 규칙을 임의의 객체 목록에 적용한다."""
    scored = [
        (-rank_score(text_of(item), request), index, item) for index, item in enumerate(items)
    ]
    scored.sort(key=lambda row: (row[0], row[1]))
    return [item for _, _, item in scored]


def _token_overlap(text: str, reference: str) -> int:
    """두 문장이 공유하는 토큰 수. 부분 문자열 검사보다 헛맞음이 적다."""
    tokens = set(textutil.tokenize(reference))
    if not tokens:
        return 0
    return sum(1 for token in set(textutil.tokenize(text)) if token in tokens)


def describe(request: PresentationRequest) -> list[str]:
    """프로파일·메시지 통제가 이번 구성에 무엇을 했는지 사람이 읽을 문장으로.

    화면의 "AI 구성 전략" 에 그대로 나가므로, 실제로 적용한 것만 적는다.
    """
    notes: list[str] = []
    profile = request.profile
    message = request.message

    if profile.expertise <= 2:
        notes.append("기술 이해도가 낮아 용어 풀이를 늘리고 설명을 더 풀었습니다")
    elif profile.expertise >= 4:
        notes.append("기술 이해도가 높아 용어 풀이를 줄이고 배경 설명을 덜어냈습니다")

    if profile.interests:
        labels = ", ".join(INTEREST_LABELS[i] for i in profile.interests)
        notes.append(f"관심 영역({labels})에 해당하는 내용을 앞으로 당겼습니다")

    if profile.prior_knowledge:
        notes.append("이미 알고 있다고 적은 내용은 뒤로 미뤘습니다")

    if message.must_convey:
        notes.append(f"반드시 전달할 메시지에 가까운 문장을 우선했습니다: {message.must_convey}")

    if message.minimize:
        notes.append(f"최소화 요청({', '.join(message.minimize)})에 해당하는 내용을 뒤로 미뤘습니다")

    if message.banned:
        notes.append(f"사용 금지 표현({', '.join(message.banned)})이 든 문장을 피했습니다")

    return notes
