"""모듈 B 프롬프트 (docs/03-audience-transform.md)."""

from __future__ import annotations

import json

from app.models.contracts import Audience, PresentationRequest, SourceAnalysis
from app.prompts import SHARED_RULES
from app.services.labels import EXPERTISE_LABELS, INTEREST_LABELS

AUDIENCE_RULES: dict[Audience, str] = {
    Audience.NEWCOMER: (
        "신입사원 대상이다. 전문용어를 풀어 쓰고, 비유와 실제 업무 예시를 넣고, "
        "배경부터 순서대로 설명하라. glossary 를 가장 충실히 채워라."
    ),
    Audience.PRACTITIONER: (
        "실무자 대상이다. 기술 세부사항과 적용 조건을 그대로 유지하라. "
        "must_keep 의 조건을 하나도 빠뜨리지 마라."
    ),
    Audience.EXECUTIVE: (
        "임원 대상이다. 결론, 효과, 리스크, 의사결정 포인트를 앞세워라. "
        "구현 세부사항보다 판단에 필요한 정보를 우선하라. emphasis 에 의사결정 포인트를 담아라."
    ),
    Audience.CUSTOMER: (
        "고객 대상이다. 고객이 얻는 가치와 적용 효과를 중심으로 설명하라. "
        "내부 조직명, 사내 시스템명, 미확인 수치, 과장 표현을 발견하면 제거하고 "
        "제거하지 못한 것은 cautions 에 남겨라."
    ),
}

STYLE_RULES = {
    "professional": "문장은 전문적이고 담백하게 쓴다.",
    "concise": "문장을 짧게 줄인다. 정보량은 줄이지 않는다.",
    "persuasive": "가치와 효과를 앞세워 설득적으로 배열한다. 없는 효과를 만들지는 않는다.",
    "friendly": "친절한 설명체로 쓴다. 어려운 말을 풀어 준다.",
}

SYSTEM = f"""너는 같은 사실을 청중에 맞춰 다시 **설계**하는 편집자다. 문장을 쉽게 바꾸는 일이 아니다.

가장 중요한 규칙: **사실은 그대로 두고, 무엇을 넣고 뺄지와 어떤 순서로 둘지를 바꾼다.**
- 원문에 없는 사실·수치·효과를 추가하는 것은 금지다. 사실 자체는 어느 청중에게나 같다.
- 그러나 이 청중의 판단에 필요 없는 사실은 덜어내고, 필요한 사실은 앞으로 당겨라.
  어느 청중에게나 같은 내용을 문장만 바꿔 내놓으면 실패다.
입력은 원문이 아니라 이미 검증된 SourceAnalysis 다.

{SHARED_RULES}

source_refs 는 입력 SourceAnalysis 항목에 붙어 있던 것을 그대로 승계하라. 새로 만들지 마라.

출력 JSON 스키마:
{{
  "tone_note": "적용한 톤을 한 줄로",
  "explanations": [{{"topic": "", "text": "", "source_refs": ["chunk-01"]}}],
  "glossary": [{{"term": "", "plain_definition": "", "source_refs": ["chunk-02"]}}],
  "emphasis": ["이 청중에게 강조할 포인트"],
  "cautions": ["내부정보/과장 등 경고"]
}}"""


def build_user_prompt(
    analysis: SourceAnalysis,
    request: PresentationRequest,
    storyline: list[str],
    glossary_limit: int | None,
) -> str:
    """`storyline` 과 `glossary_limit` 은 services/audience.py 가 넘긴다.

    그 값을 여기서 다시 적지 않는 이유는, 조건 화면이 생성 전에 같은 순서를 미리 보여주기
    때문이다. 프롬프트가 따로 놀면 화면이 예고한 구성과 결과가 어긋난다.
    (프롬프트 모듈이 서비스 모듈을 import 하면 순환이 되므로 인자로 받는다.)
    """
    payload = {
        "core_message": analysis.core_message,
        "technical_points": [i.model_dump() for i in analysis.technical_points],
        "key_features": [i.model_dump() for i in analysis.key_features],
        "numbers": [n.model_dump() for n in analysis.numbers],
        "terms": [t.model_dump() for t in analysis.terms],
        "must_keep": [m.model_dump() for m in analysis.must_keep],
    }
    original_terms = (
        "원문 영문 용어를 그대로 두고 괄호로 한국어 설명을 덧붙여라."
        if request.preserve_original_terms
        else "영문 용어는 한국어로 바꾸되 최초 1회는 원어를 병기하라."
    )

    outline = "\n".join(f"{i}. {topic}" for i, topic in enumerate(storyline, start=1))
    profile_block = _profile_block(request)
    message_block = _message_block(request)
    glossary_rule = (
        "glossary 는 원문 용어를 빠짐없이 담아라."
        if glossary_limit is None
        else f"glossary 는 최대 {glossary_limit}개만 담아라. 이 청중에게는 용어 풀이가 우선순위가 아니다."
        if glossary_limit
        else "glossary 는 비워 둬라. 이 청중에게 용어 풀이는 판단에 도움이 되지 않는다."
    )

    return f"""청중: {request.audience.value}
{AUDIENCE_RULES[request.audience]}

explanations 의 topic 을 아래 순서 그대로 만들어라. 이것이 이 청중의 이야기 구성이다.
{outline}

- 원문에 근거가 없어 채울 수 없는 항목은 건너뛰어라. 지어내지 마라.
- 순서를 바꾸거나 새 topic 을 임의로 추가하지 마라. 화면이 생성 전에 이 순서를 예고한다.
- 각 topic 에는 그 자리에 필요한 사실만 골라 담아라. SourceAnalysis 를 전부 옮기는 것이 아니다.
{glossary_rule}
{profile_block}{message_block}
표현 스타일: {request.style.value} — {STYLE_RULES.get(request.style.value, '')}
원어 유지: {original_terms}
필수 키워드: {', '.join(request.keywords) or '없음'}

SourceAnalysis:
{json.dumps(payload, ensure_ascii=False, indent=2)}

위 사실만으로 청중에 맞춘 JSON 을 작성하라."""


def _profile_block(request: PresentationRequest) -> str:
    """청중 프로파일. 청중 하나로는 못 잡는 '어느 정도로, 무엇에 관심'을 전한다."""
    profile = request.profile
    lines = [
        f"기술 이해도: {profile.expertise}/5 ({EXPERTISE_LABELS.get(profile.expertise, '')})"
    ]
    if profile.expertise <= 2:
        lines.append("  - 사전 지식을 가정하지 마라. 용어가 처음 나올 때마다 풀어 쓰고 단계를 건너뛰지 마라.")
    elif profile.expertise >= 4:
        lines.append("  - 기본 개념 설명에 분량을 쓰지 마라. 아는 사람에게 필요한 깊이로 바로 들어가라.")

    if profile.interests:
        labels = ", ".join(INTEREST_LABELS[i] for i in profile.interests)
        lines.append(f"관심 영역: {labels}")
        lines.append(
            "  - 이 축에 해당하는 사실을 각 topic 안에서 앞에 두어라. "
            "원문에 없는 축은 만들지 마라 — 없으면 없는 대로 둔다."
        )

    if profile.prior_knowledge:
        lines.append(f"이미 알고 있는 것: {profile.prior_knowledge}")
        lines.append("  - 여기 적힌 내용은 다시 길게 설명하지 마라. 짧게 언급하고 넘어가라.")

    return "\n청중 프로파일\n" + "\n".join(lines) + "\n"


def _message_block(request: PresentationRequest) -> str:
    """발표자가 지정한 메시지 통제. 사실을 바꾸는 권한은 없다."""
    message = request.message
    lines: list[str] = []

    if message.must_convey:
        lines.append(f"반드시 전달할 메시지: {message.must_convey}")
        lines.append(
            "  - 이 메시지를 뒷받침하는 원문 사실을 앞에 배치하라. "
            "뒷받침할 사실이 원문에 없으면 지어내지 말고 그대로 두어라."
        )
    if message.minimize:
        lines.append(f"최소화: {', '.join(message.minimize)}")
        lines.append("  - 이 주제는 분량을 줄여 뒤에 두어라. 사실 자체를 삭제하지는 마라.")
    if message.banned:
        lines.append(f"사용 금지 표현: {', '.join(message.banned)}")
        lines.append("  - 이 표현을 쓰지 마라. 같은 뜻의 과장 표현으로 바꿔 쓰는 것도 금지다.")

    if not lines:
        return ""
    return "\n메시지 통제 (발표자 지정)\n" + "\n".join(lines) + "\n"
