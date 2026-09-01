"""모듈 D 프롬프트 (docs/05-presentation-support.md)."""

from __future__ import annotations

import json

from app.models.contracts import (
    Audience,
    AudienceContent,
    PresentationRequest,
    SlideDeck,
    SourceAnalysis,
)
from app.prompts import SHARED_RULES

AUDIENCE_QUESTIONS: dict[Audience, str] = {
    Audience.NEWCOMER: "용어의 뜻, 왜 필요한지, 자기 업무와 무슨 관계인지를 주로 묻는다.",
    Audience.PRACTITIONER: "적용 조건, 예외 케이스, 기존 방식과의 차이, 성능을 주로 묻는다.",
    Audience.EXECUTIVE: "비용, 일정, 리스크, 의사결정 포인트, ROI 를 주로 묻는다.",
    Audience.CUSTOMER: "도입 효과, 우리 환경 적용 가능성, 리스크와 지원 범위를 주로 묻는다.",
}

SYSTEM = f"""너는 발표자의 리허설을 돕는 코치다. 슬라이드별 발표 스크립트와 예상 질문을 만든다.

{SHARED_RULES}

추가 규칙:
- 스크립트는 슬라이드당 30~60초 분량(한국어 200~380자)으로 쓴다.
- must_say 는 발표자가 반드시 말해야 할 한 문장이다.
- 예상 질문은 3~5개이며 청중에 따라 달라야 한다.
- 답변은 주어진 사실로만 구성하고 source_refs 를 붙인다.
- 근거로 답할 수 없는 질문에는 답을 지어내지 말고 answer 를 "원문 확인 필요: ..." 로 시작하고
  source_refs 를 빈 배열로 두어라.

출력 JSON 스키마:
{{
  "scripts": [{{"slide_id": "slide-1", "script": "", "must_say": "", "duration_seconds": 45}}],
  "qa": [{{"question": "", "answer": "", "source_refs": ["chunk-04"], "asked_by": "customer"}}],
  "rehearsal_cards": [{{"question": "", "why": "", "recommended_slide": "slide-3"}}]
}}"""


def build_user_prompt(
    deck: SlideDeck,
    content: AudienceContent,
    analysis: SourceAnalysis,
    request: PresentationRequest,
) -> str:
    payload = {
        "slide_deck": deck.model_dump(mode="json"),
        "terms": [t.model_dump() for t in analysis.terms],
        "numbers": [n.model_dump() for n in analysis.numbers],
        "must_keep": [m.model_dump() for m in analysis.must_keep],
        "emphasis": content.emphasis,
    }
    total_seconds = request.duration_minutes * 60
    return f"""청중: {request.audience.value} — {AUDIENCE_QUESTIONS[request.audience]}
전체 발표 시간: {request.duration_minutes}분({total_seconds}초). 스크립트 시간 합계를 여기에 맞춰라.
asked_by 는 모두 "{request.audience.value}" 로 쓴다.

입력:
{json.dumps(payload, ensure_ascii=False, indent=2)}

슬라이드 수만큼 스크립트를 만들고, 예상 질문은 3~5개 만들어라."""
