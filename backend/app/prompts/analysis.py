"""모듈 A 프롬프트 (docs/02-document-analysis.md)."""

from __future__ import annotations

from app.models.contracts import Chunk
from app.prompts import SHARED_RULES

SYSTEM = f"""너는 기술문서에서 사실만 구조화해 추출하는 분석기다.
문서를 요약하거나 재해석하지 말고, 문서에 적혀 있는 것만 뽑아라.

{SHARED_RULES}

출력 JSON 스키마:
{{
  "core_message": "문서 전체의 핵심을 한 문장으로",
  "technical_points": [{{"text": "", "source_refs": ["chunk-01"]}}],
  "key_features": [{{"text": "", "source_refs": ["chunk-01"]}}],
  "numbers": [{{"value": "94.2", "unit": "%", "meaning": "이 수치가 무엇인지", "source_refs": ["chunk-03"]}}],
  "terms": [{{"term": "", "definition": "문서에 적힌 정의를 쉬운 말로", "source_refs": ["chunk-02"]}}],
  "must_keep": [{{"text": "반드시 유지해야 하는 조건/주의사항", "source_refs": ["chunk-04"]}}],
  "unverified": ["근거를 찾지 못한 항목 설명"]
}}

주의:
- numbers 의 value 는 원문에 적힌 값을 그대로 쓴다. 반올림, 환산, 추정 금지.
- must_keep 에는 "단, ~인 경우", "~해야 한다", "~ 이상 필요" 같은 조건부 서술을 담는다.
  이 항목이 누락되면 발표자료가 원문을 과도하게 단순화하게 된다."""


def build_user_prompt(chunks: list[Chunk], keywords: list[str], max_chars: int) -> str:
    parts: list[str] = []
    used = 0
    for chunk in chunks:
        block = f"[{chunk.id} | 페이지 {chunk.page}]\n{chunk.text}"
        if used + len(block) > max_chars:
            break
        parts.append(block)
        used += len(block)

    keyword_line = ""
    if keywords:
        keyword_line = (
            "\n발표에서 반드시 다뤄야 하는 키워드: "
            + ", ".join(keywords)
            + "\n이 키워드와 관련된 사실이 문서에 있으면 우선적으로 추출하라."
        )

    return f"""다음은 분석할 기술문서의 원문 chunk 다.

{chr(10).join(parts)}
{keyword_line}

위 chunk 만을 근거로 JSON 을 작성하라."""
