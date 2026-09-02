"""모듈 C 프롬프트 (docs/04-slide-planner.md)."""

from __future__ import annotations

import json

from app.models.contracts import AudienceContent, PresentationRequest, SourceAnalysis
from app.prompts import SHARED_RULES

SYSTEM = f"""너는 발표 자료의 구조를 설계하는 기획자다.
주어진 청중용 설명과 사실만으로 슬라이드 덱을 구성한다.

{SHARED_RULES}

권장 구성: 1) 발표 목적/문제 배경 2) 기술 또는 해결 방식 3) 작동 원리/핵심 내용
4) 주요 장점 또는 가치 5) 결론 및 다음 행동

슬라이드 규칙:
- takeaway 는 그 슬라이드에서 청중이 가져갈 결론 한 문장이다.
- bullets 는 3~5개, 각 40자 내외. 문단을 그대로 붙여넣지 마라.
- 모든 슬라이드에 source_refs 를 1개 이상 반드시 넣어라.
- visual_suggestion 은 "무엇을 그릴지" 한 줄로 쓴다.
- speaker_notes 는 짧은 씨앗 문장이면 충분하다.

출력 JSON 스키마:
{{
  "title": "덱 제목",
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
필수 키워드(덱 안에 최소 1회 등장): {', '.join(request.keywords) or '없음'}

입력:
{json.dumps(payload, ensure_ascii=False, indent=2)}

정확히 {slide_count}장의 슬라이드를 만들어라."""
