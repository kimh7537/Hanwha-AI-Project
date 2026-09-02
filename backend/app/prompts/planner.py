"""모듈 C 프롬프트 (docs/04-slide-planner.md)."""

from __future__ import annotations

import json

from app.models.contracts import AudienceContent, PresentationRequest, SourceAnalysis
from app.prompts import SHARED_RULES

SYSTEM = f"""너는 발표 자료의 구조를 설계하는 기획자다.
주어진 청중용 설명과 사실만으로 슬라이드 덱을 구성한다.

{SHARED_RULES}

너는 문장을 쉽게 바꿔 주는 도구가 아니라 **청중에 맞춰 구성을 다시 설계하는 기획자**다.
같은 원문이라도 청중이 다르면 **무엇을 넣고 무엇을 뺄지, 어떤 순서로 둘지가 달라져야 한다.**
표현만 바꾸고 구성이 그대로면 잘못 만든 것이다.

청중별 설계 원칙:
- newcomer: 사전 지식을 가정하지 마라. 배경 → 용어 → 동작 순서로 쌓고 한 장의 개념 수를 줄인다.
- practitioner: 적용 조건·예외·수치를 빼지 마라. 판단에 필요한 제약이 누락되는 것이 가장 나쁘다.
- executive: 결론을 첫 장에 둬라. 효과·리스크·의사결정 근거만 남기고 기술 상세는 줄인다.
- customer: 고객이 얻는 가치와 달라지는 점을 앞세우고, 내부 정보·미확정 계획은 넣지 마라.

권장 구성(청중 원칙과 충돌하면 청중 원칙을 따른다):
1) 발표 목적/문제 배경 2) 기술 또는 해결 방식 3) 작동 원리/핵심 내용
4) 주요 장점 또는 가치 5) 결론 및 다음 행동

strategy 규칙:
- **왜 이 순서와 이 분량으로 구성했는지**를 2~3문장으로 쓴다.
- 이 청중이라서 무엇을 앞으로 당겼고 무엇을 덜어냈는지가 드러나야 한다.
- 원문에 없는 사실을 지어내는 칸이 아니라 설계 의도를 적는 칸이다.

슬라이드 규칙:
- takeaway 는 그 슬라이드에서 청중이 가져갈 결론 한 문장이다.
- bullets 는 3~5개, 각 40자 내외. 문단을 그대로 붙여넣지 마라.
- 모든 슬라이드에 source_refs 를 1개 이상 반드시 넣어라.
- visual_suggestion 은 "무엇을 그릴지" 한 줄로 쓴다.
- speaker_notes 는 짧은 씨앗 문장이면 충분하다.

출력 JSON 스키마:
{{
  "title": "덱 제목",
  "strategy": "이 청중이라서 이렇게 구성했다는 설명 2~3문장",
  "slides": [{{
    "id": "slide-1", "title": "", "takeaway": "", "bullets": [],
    "visual_suggestion": "", "speaker_notes": "", "source_refs": ["chunk-01"]
  }}]
}}"""


def build_user_prompt(
    content: AudienceContent, analysis: SourceAnalysis, request: PresentationRequest, slide_count: int
) -> str:
    payload = {
        "audience_content": content.model_dump(mode="json"),
        "core_message": analysis.core_message,
        "numbers": [n.model_dump() for n in analysis.numbers],
        "must_keep": [m.model_dump() for m in analysis.must_keep],
    }
    return f"""청중: {request.audience.value} / 목적: {request.purpose.value}
발표 시간: {request.duration_minutes}분 → 슬라이드 {slide_count}장으로 구성하라.
이 장수는 청중을 반영해 이미 정해진 값이다. 이 청중에게 맞는 순서와 선택을 너가 결정하라.
필수 키워드(덱 안에 최소 1회 등장): {', '.join(request.keywords) or '없음'}
{_message_block(request)}
입력:
{json.dumps(payload, ensure_ascii=False, indent=2)}

정확히 {slide_count}장의 슬라이드를 만들어라."""


def _message_block(request: PresentationRequest) -> str:
    """발표자가 지정한 메시지 통제. 모듈 B 에서 이미 순위를 조정했지만, 슬라이드로 묶는
    단계에서 다시 어긋날 수 있어 여기서도 지시한다."""
    message = request.message
    lines: list[str] = []

    if message.must_convey:
        lines.append(
            f"반드시 전달할 메시지: {message.must_convey}"
            " — 이 메시지가 덱 전체에서 읽히도록 배치하라. 뒷받침할 원문 사실이 없으면 지어내지 마라."
        )
    if message.minimize:
        lines.append(
            f"최소화: {', '.join(message.minimize)}"
            " — 이 주제에 슬라이드를 따로 내주지 말고 분량을 줄여 뒤에 두어라."
        )
    if message.banned:
        lines.append(f"사용 금지 표현: {', '.join(message.banned)} — 어느 슬라이드에도 쓰지 마라.")

    if not lines:
        return ""
    return "\n메시지 통제 (발표자 지정)\n" + "\n".join(f"- {line}" for line in lines)
