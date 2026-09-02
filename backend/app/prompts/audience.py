"""모듈 B 프롬프트 (docs/03-audience-transform.md)."""

from __future__ import annotations

import json

from app.models.contracts import Audience, PresentationRequest, SourceAnalysis
from app.prompts import SHARED_RULES

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

SYSTEM = f"""너는 동일한 사실을 청중에 맞춰 다시 설명하는 편집자다.

가장 중요한 규칙: **사실은 유지하고 표현의 깊이만 바꾼다.**
청중 맞춤이라는 이유로 원문에 없는 사실, 수치, 효과를 추가하는 것은 금지다.
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


def build_user_prompt(analysis: SourceAnalysis, request: PresentationRequest) -> str:
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

    return f"""청중: {request.audience.value}
{AUDIENCE_RULES[request.audience]}

표현 스타일: {request.style.value} — {STYLE_RULES.get(request.style.value, '')}
원어 유지: {original_terms}
필수 키워드: {', '.join(request.keywords) or '없음'}

SourceAnalysis:
{json.dumps(payload, ensure_ascii=False, indent=2)}

위 사실만으로 청중에 맞춘 JSON 을 작성하라."""
