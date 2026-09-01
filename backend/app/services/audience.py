"""모듈 B: SourceAnalysis -> AudienceContent (docs/03-audience-transform.md).

핵심 차별화 기능. 절대 규칙은 '사실은 유지하고 표현의 깊이만 바꾼다'이다.
휴리스틱 경로는 문장을 지어내지 않고 SourceAnalysis 의 문장을 고르고 재배열한다.
"""

from __future__ import annotations

import re

from app.llm.base import RunContext
from app.models.contracts import (
    Audience,
    AudienceContent,
    AudienceExplanation,
    GlossaryItem,
    NumberFact,
    PresentationRequest,
    SourceAnalysis,
    Style,
)
from app.prompts import audience as audience_prompt
from app.services import textutil
from app.services.evidence import inherit_refs, valid_refs

STAGE = "청중 변환"

_TONE_NOTES: dict[Audience, str] = {
    Audience.NEWCOMER: "용어를 풀어 설명하고 배경부터 순서대로",
    Audience.PRACTITIONER: "기술 세부사항과 적용 조건을 그대로 유지",
    Audience.EXECUTIVE: "결론과 효과, 리스크와 의사결정 포인트 우선",
    Audience.CUSTOMER: "고객 가치와 적용 효과 중심, 내부 정보는 경고 처리",
}

_STYLE_NOTES: dict[Style, str] = {
    Style.PROFESSIONAL: "전문적인 톤",
    Style.CONCISE: "간결한 톤",
    Style.PERSUASIVE: "설득형 톤",
    Style.FRIENDLY: "친절한 설명형 톤",
}

_EMPHASIS: dict[Audience, list[str]] = {
    Audience.NEWCOMER: ["이 기술이 왜 필요한지", "용어의 뜻", "내 업무와의 연결"],
    Audience.PRACTITIONER: ["적용 조건과 예외", "기존 방식과의 차이", "성능 수치"],
    Audience.EXECUTIVE: ["도입 효과", "리스크와 전제 조건", "의사결정에 필요한 판단 근거"],
    Audience.CUSTOMER: ["고객이 얻는 가치", "적용 시 달라지는 점", "확인이 필요한 전제"],
}


_strip_english_gloss = textutil.strip_english_gloss


def _apply_options(text: str, request: PresentationRequest) -> str:
    result = text if request.preserve_original_terms else _strip_english_gloss(text)
    if request.style is Style.CONCISE:
        result = textutil.shorten(result, 110)
    return textutil.normalize(result)


def _effect_numbers(analysis: SourceAnalysis) -> list[NumberFact]:
    """도입 효과 수치. 실제 성과 서술이 앞에 오도록 정렬한다."""
    scored = [
        (textutil.effect_strength(n.meaning), n)
        for n in analysis.numbers
        if textutil.effect_strength(n.meaning) > 0
    ]
    scored.sort(key=lambda row: row[0], reverse=True)
    return [number for _, number in scored]


def _join(sentences: list[str], limit: int) -> str:
    """문장을 이어 붙인다. 새로운 사실을 추가하지 않는다."""
    picked: list[str] = []
    for sentence in sentences:
        cleaned = textutil.normalize(sentence)
        if cleaned and cleaned not in picked:
            picked.append(cleaned)
        if len(picked) >= limit:
            break
    return " ".join(picked)


def _explanation(
    topic: str, sentences: list[str], refs: list[str], request: PresentationRequest, limit: int = 3
) -> AudienceExplanation | None:
    text = _apply_options(_join(sentences, limit), request)
    if not text:
        return None
    return AudienceExplanation(topic=topic, text=text, source_refs=refs)


def transform_heuristic(
    analysis: SourceAnalysis, request: PresentationRequest
) -> AudienceContent:
    audience = request.audience
    explanations: list[AudienceExplanation] = []

    core_refs = inherit_refs(*[i.source_refs for i in analysis.technical_points[:1]])
    tech = analysis.technical_points
    features = analysis.key_features
    conditions = analysis.must_keep
    effects = _effect_numbers(analysis)

    def add(topic: str, sentences: list[str], refs: list[str], limit: int = 3) -> None:
        item = _explanation(topic, sentences, refs, request, limit)
        if item:
            explanations.append(item)

    if audience is Audience.NEWCOMER:
        add("무엇을 하는 기술인가", [analysis.core_message], core_refs, 1)
        add(
            "왜 필요한가",
            [n.meaning for n in analysis.numbers[:2]],
            inherit_refs(*[n.source_refs for n in analysis.numbers[:2]]),
        )
        add(
            "어떻게 동작하나",
            [i.text for i in features[:3]] or [i.text for i in tech[:3]],
            inherit_refs(*[i.source_refs for i in (features[:3] or tech[:3])]),
        )
        add(
            "기억해야 할 조건",
            [i.text for i in conditions[:2]],
            inherit_refs(*[i.source_refs for i in conditions[:2]]),
            2,
        )

    elif audience is Audience.PRACTITIONER:
        add("기술 구성", [i.text for i in tech[:4]], inherit_refs(*[i.source_refs for i in tech[:4]]), 4)
        add(
            "성능과 측정 조건",
            [n.meaning for n in analysis.numbers[:4]],
            inherit_refs(*[n.source_refs for n in analysis.numbers[:4]]),
            4,
        )
        # 실무자에게는 must_keep 을 하나도 빠뜨리지 않는다
        add(
            "적용 조건과 제약",
            [i.text for i in conditions],
            inherit_refs(*[i.source_refs for i in conditions]),
            len(conditions) or 1,
        )

    elif audience is Audience.EXECUTIVE:
        # 덱 마지막의 "결론 및 다음 행동" 과 제목이 겹치지 않게 한다.
        add("한 줄 결론", [analysis.core_message], core_refs, 1)
        add(
            "도입 효과",
            [n.meaning for n in (effects or analysis.numbers[:2])],
            inherit_refs(*[n.source_refs for n in (effects or analysis.numbers[:2])]),
            2,
        )
        add(
            "리스크와 전제 조건",
            [i.text for i in conditions[:3]],
            inherit_refs(*[i.source_refs for i in conditions[:3]]),
            3,
        )
        add(
            "판단에 필요한 기술 요약",
            [i.text for i in tech[:2]],
            inherit_refs(*[i.source_refs for i in tech[:2]]),
            2,
        )

    else:  # CUSTOMER
        add("제공하는 가치", [analysis.core_message], core_refs, 1)
        add(
            "적용 효과",
            [n.meaning for n in (effects or analysis.numbers[:2])],
            inherit_refs(*[n.source_refs for n in (effects or analysis.numbers[:2])]),
            2,
        )
        add(
            "동작 방식",
            [i.text for i in tech[:2]],
            inherit_refs(*[i.source_refs for i in tech[:2]]),
            2,
        )
        add(
            "적용 전 확인이 필요한 조건",
            [i.text for i in conditions[:3]],
            inherit_refs(*[i.source_refs for i in conditions[:3]]),
            3,
        )

    # 용어 풀이: 신입사원에게 가장 많이, 임원에게 가장 적게
    glossary_limit = {
        Audience.NEWCOMER: len(analysis.terms),
        Audience.PRACTITIONER: 2,
        Audience.EXECUTIVE: 0,
        Audience.CUSTOMER: 2,
    }[audience]
    glossary = [
        GlossaryItem(
            term=term.term if request.preserve_original_terms else _strip_english_gloss(term.term),
            plain_definition=_apply_options(term.definition, request),
            source_refs=list(term.source_refs),
        )
        for term in analysis.terms[:glossary_limit]
    ]

    content = AudienceContent(
        audience=audience,
        tone_note=f"{_TONE_NOTES[audience]} · {_STYLE_NOTES.get(request.style, '')}",
        explanations=explanations,
        glossary=glossary,
        emphasis=list(_EMPHASIS[audience]),
    )

    content.cautions = build_cautions(analysis, content, request)
    return content


def build_cautions(
    analysis: SourceAnalysis, content: AudienceContent, request: PresentationRequest
) -> list[str]:
    """고객용 경고. LLM 경로에서도 반드시 적용되도록 분리해 둔다."""
    cautions: list[str] = list(content.cautions)

    if analysis.unverified:
        cautions.append(
            f"원문에서 근거를 찾지 못한 항목이 {len(analysis.unverified)}건 있습니다. "
            "발표 전 확인이 필요합니다."
        )

    if request.audience is not Audience.CUSTOMER:
        return _dedupe(cautions)

    body = " ".join(e.text for e in content.explanations)
    body += " " + " ".join(g.plain_definition for g in content.glossary)

    internal = textutil.contains_any(body, textutil.INTERNAL_MARKERS)
    if internal:
        cautions.append(
            "고객용 자료에 내부 정보로 보이는 표현이 남아 있습니다: "
            + ", ".join(sorted(set(internal)))
            + ". 공개 전 제거하거나 승인 여부를 확인하세요."
        )

    exaggeration = textutil.contains_any(body, textutil.EXAGGERATION_MARKERS)
    if exaggeration:
        cautions.append(
            "과장으로 읽힐 수 있는 표현이 있습니다: " + ", ".join(sorted(set(exaggeration)))
        )

    cautions.append("고객 공개 자료입니다. 발표 전 담당자 검토가 필요합니다.")
    return _dedupe(cautions)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    return [i for i in items if not (i in seen or seen.add(i))]


def transform(
    analysis: SourceAnalysis, request: PresentationRequest, ctx: RunContext
) -> AudienceContent:
    """모듈 B 진입점."""
    payload = ctx.call_json(
        stage=STAGE,
        system=audience_prompt.SYSTEM,
        user=audience_prompt.build_user_prompt(analysis, request),
        max_tokens=2500,
    )

    content: AudienceContent | None = None
    if payload is not None:
        try:
            payload["audience"] = request.audience.value
            content = AudienceContent(**payload)
        except Exception as exc:  # noqa: BLE001
            ctx.note_fallback(STAGE, f"LLM 응답이 계약과 맞지 않습니다: {exc}")
            content = None
        else:
            # 계약의 필드에 기본값이 있어 형태가 다른 JSON 도 '빈 결과' 로 통과한다
            if not content.explanations:
                ctx.note_fallback(STAGE, "LLM 응답이 계약과 맞지 않습니다: 청중용 설명이 없습니다")
                content = None

    if content is None:
        return transform_heuristic(analysis, request)

    # LLM 이 만들어낸 근거 id 를 실제 존재하는 것만 남긴다
    known = {e.id for e in analysis.source_evidence}
    for explanation in content.explanations:
        explanation.source_refs = valid_refs(explanation.source_refs, known)
    for term in content.glossary:
        term.source_refs = valid_refs(term.source_refs, known)

    content.audience = request.audience
    if not content.tone_note:
        content.tone_note = _TONE_NOTES[request.audience]
    content.cautions = build_cautions(analysis, content, request)
    return content
