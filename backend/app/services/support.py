"""모듈 D: SlideDeck -> PresentationSupport (docs/05-presentation-support.md).

근거로 답할 수 없는 질문에는 답을 지어내지 않고 "원문 확인 필요"로 표시한다.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.llm.base import RunContext
from app.models.contracts import (
    Audience,
    AudienceContent,
    PresentationRequest,
    PresentationSupport,
    QAItem,
    RehearsalCard,
    SlideDeck,
    SlideScript,
    SourceAnalysis,
)
from app.prompts import support as support_prompt
from app.services import textutil
from app.services.evidence import inherit_refs, valid_refs

STAGE = "발표 지원"

# 한국어 발표 속도(초당 글자 수) 추정치. 스크립트 길이 <-> 시간 환산에 쓴다.
CHARS_PER_SECOND = 5.0
MIN_SECONDS = 25
MAX_SECONDS = 75

_UNVERIFIED_PREFIX = "원문 확인 필요"


@dataclass
class _Fact:
    text: str
    refs: list[str]


def _already_said(candidate: str, used: list[str]) -> bool:
    """이미 말한 문장과 사실상 같은 내용인지.

    bullets 는 takeaway/설명을 줄인 형태라 문자열이 완전히 같지는 않다.
    토큰 겹침으로 판단해 같은 말이 반복되지 않게 한다.
    """
    tokens = set(textutil.tokenize(candidate))
    if not tokens:
        return True
    for previous in used:
        previous_tokens = set(textutil.tokenize(previous))
        if not previous_tokens:
            continue
        if len(tokens & previous_tokens) / len(tokens) >= 0.7:
            return True
    return False


def _effect_facts(analysis: SourceAnalysis) -> list[_Fact]:
    """도입 효과 서술. 실제 성과 문장이 앞에 오도록 정렬한다."""
    scored = [
        (textutil.effect_strength(n.meaning), _Fact(n.meaning, list(n.source_refs)))
        for n in analysis.numbers
        if textutil.effect_strength(n.meaning) > 0
    ]
    scored.sort(key=lambda row: row[0], reverse=True)
    return [fact for _, fact in scored]


def _performance_facts(analysis: SourceAnalysis) -> list[_Fact]:
    markers = ("정확도", "응답", "처리량", "점수", "성능")
    return [
        _Fact(f"{n.value}{n.unit} — {n.meaning}", list(n.source_refs))
        for n in analysis.numbers
        if textutil.contains_any(n.meaning, markers)
    ]


def _condition_facts(analysis: SourceAnalysis) -> list[_Fact]:
    return [_Fact(m.text, list(m.source_refs)) for m in analysis.must_keep]


def _schedule_facts(analysis: SourceAnalysis) -> list[_Fact]:
    markers = ("일정", "확정", "예정", "분기", "승인")
    facts: list[_Fact] = []
    for item in analysis.must_keep + analysis.technical_points:
        if textutil.contains_any(item.text, markers):
            facts.append(_Fact(item.text, list(item.source_refs)))
    return facts


def _answer_from(facts: list[_Fact], limit: int = 2) -> tuple[str, list[str]]:
    """사실을 이어 붙여 답변을 만든다. 같은 문장이 여러 번 들어가지 않게 한다."""
    picked: list[_Fact] = []
    seen: list[str] = []

    for fact in facts:
        text = textutil.normalize(fact.text)
        if not text or _already_said(text, seen):
            continue
        picked.append(fact)
        seen.append(text)
        if len(picked) >= limit:
            break

    if not picked:
        return "", []
    return " ".join(seen), inherit_refs(*[f.refs for f in picked])


def _qa(question: str, facts: list[_Fact], audience: Audience, missing_hint: str) -> QAItem:
    answer, refs = _answer_from(facts)
    if not answer:
        return QAItem(
            question=question,
            answer=f"{_UNVERIFIED_PREFIX}: {missing_hint}",
            source_refs=[],
            asked_by=audience,
        )
    return QAItem(question=question, answer=answer, source_refs=refs, asked_by=audience)


def build_qa_heuristic(analysis: SourceAnalysis, request: PresentationRequest) -> list[QAItem]:
    audience = request.audience
    effects = _effect_facts(analysis)
    performance = _performance_facts(analysis)
    conditions = _condition_facts(analysis)

    # 원어 유지 설정을 청중 변환과 동일하게 적용한다.
    # 그렇지 않으면 용어 풀이에는 "임베딩", 질문에는 "임베딩(embedding)" 이 나온다.
    def term_label(term: str) -> str:
        return term if request.preserve_original_terms else textutil.strip_english_gloss(term)

    terms = [
        _Fact(f"{term_label(t.term)}: {t.definition}", list(t.source_refs))
        for t in analysis.terms
    ]

    items: list[QAItem] = []

    if audience is Audience.NEWCOMER:
        if analysis.terms:
            first = analysis.terms[0]
            items.append(
                _qa(
                    f"{term_label(first.term)}이(가) 무슨 뜻인가요?",
                    terms,
                    audience,
                    "용어 정의를 원문에서 찾지 못했습니다.",
                )
            )
        items.append(
            _qa(
                "이 기술이 왜 필요한가요?",
                effects or performance,
                audience,
                "필요성을 뒷받침하는 수치를 찾지 못했습니다.",
            )
        )
        items.append(
            _qa(
                "제 업무에서는 무엇이 달라지나요?",
                effects,
                audience,
                "업무 변화에 대한 근거가 원문에 없습니다.",
            )
        )
        items.append(
            _qa(
                "사용할 때 주의할 점이 있나요?",
                conditions,
                audience,
                "주의사항을 원문에서 찾지 못했습니다.",
            )
        )

    elif audience is Audience.PRACTITIONER:
        items.append(
            _qa(
                "적용할 때 지켜야 하는 조건은 무엇인가요?",
                conditions,
                audience,
                "적용 조건이 원문에 없습니다.",
            )
        )
        items.append(
            _qa(
                "기존 방식과 비교하면 어떤가요?",
                performance,
                audience,
                "비교 수치를 원문에서 찾지 못했습니다.",
            )
        )
        items.append(
            _qa(
                "예외 상황에서는 어떻게 동작하나요?",
                conditions[1:] or conditions,
                audience,
                "예외 처리에 대한 서술이 원문에 없습니다.",
            )
        )
        items.append(
            _qa(
                "성능 수치는 어떤 조건에서 측정한 값인가요?",
                performance,
                audience,
                "측정 조건이 원문에 없습니다.",
            )
        )

    elif audience is Audience.EXECUTIVE:
        items.append(
            _qa(
                "도입 효과를 수치로 말하면 어떻게 되나요?",
                effects,
                audience,
                "효과를 나타내는 수치가 원문에 없습니다.",
            )
        )
        items.append(
            _qa(
                "리스크나 전제 조건은 무엇인가요?",
                conditions,
                audience,
                "리스크에 대한 서술이 원문에 없습니다.",
            )
        )
        items.append(
            _qa(
                "일정은 어떻게 되나요?",
                _schedule_facts(analysis),
                audience,
                "일정에 대한 정보가 원문에 없습니다.",
            )
        )
        items.append(
            _qa("도입 비용은 얼마나 드나요?", [], audience, "비용에 대한 정보가 원문에 없습니다.")
        )

    else:  # CUSTOMER
        items.append(
            _qa(
                "도입하면 무엇이 달라지나요?",
                effects,
                audience,
                "도입 효과 수치를 원문에서 찾지 못했습니다.",
            )
        )
        items.append(
            _qa(
                "저희 환경에도 적용할 수 있나요?",
                conditions,
                audience,
                "적용 조건이 원문에 없습니다.",
            )
        )
        items.append(
            _qa(
                "성능은 어느 정도인가요?",
                performance,
                audience,
                "성능 수치를 원문에서 찾지 못했습니다.",
            )
        )
        items.append(
            _qa(
                "도입 시 리스크는 무엇인가요?",
                conditions[1:] or conditions,
                audience,
                "리스크에 대한 서술이 원문에 없습니다.",
            )
        )

    return items[:5]


def _speech(takeaway: str) -> str:
    """takeaway 를 발화체 한 문장으로."""
    cleaned = textutil.normalize(takeaway)
    if not cleaned:
        return ""
    if cleaned.endswith("."):
        cleaned = cleaned[:-1]
    if cleaned.endswith("다"):
        return f"{cleaned}."
    return f"{cleaned}라는 점을 기억해 주시기 바랍니다."


def build_scripts_heuristic(
    deck: SlideDeck,
    content: AudienceContent,
    request: PresentationRequest,
    analysis: SourceAnalysis | None = None,
) -> list[SlideScript]:
    if not deck.slides:
        return []

    # 슬라이드가 인용한 chunk 의 원문 문장. 스크립트 분량이 모자랄 때 발표 멘트로 보강한다.
    evidence_text = {e.id: e.text for e in (analysis.source_evidence if analysis else [])}

    total_seconds = request.duration_minutes * 60
    per_slide = total_seconds / len(deck.slides)
    budget_seconds = int(max(MIN_SECONDS, min(MAX_SECONDS, per_slide)))
    budget_chars = int(budget_seconds * CHARS_PER_SECOND)
    is_customer = request.audience is Audience.CUSTOMER

    scripts: list[SlideScript] = []
    for index, slide in enumerate(deck.slides):
        opener = "먼저" if index == 0 else "다음으로"
        parts: list[str] = [f"{opener} {slide.title}에 대해 말씀드리겠습니다."]

        # speaker_notes 에는 청중용 설명 원문이 들어 있다.
        # bullets 는 그것을 잘라낸 형태라 그대로 읽으면 문장이 끊겨 들리므로 쓰지 않는다.
        for source in (slide.speaker_notes, slide.takeaway):
            for sentence in textutil.split_sentences(source or ""):
                parts.append(textutil.normalize(sentence))

        # 분량이 남으면 이 슬라이드가 실제로 인용한 원문 문장으로 채운다.
        # 없는 내용을 지어내지 않으면서 발표 시간을 맞추는 유일한 방법이다.
        for ref in slide.source_refs:
            for sentence in textutil.split_sentences(evidence_text.get(ref, "")):
                # 고객 발표에서는 보강 문장에 내부 정보가 섞여 들어가지 않게 한다
                if is_customer and textutil.contains_any(sentence, textutil.INTERNAL_MARKERS):
                    continue
                parts.append(textutil.normalize(sentence))

        script = ""
        used: list[str] = []
        for part in parts:
            if not part or _already_said(part, used):
                continue
            candidate = f"{script} {part}".strip()
            if len(candidate) > budget_chars:
                if script:
                    continue  # 더 짧은 뒤 문장이 남은 자리에 들어갈 수 있다
                break
            script = candidate
            used.append(part)

        scripts.append(
            SlideScript(
                slide_id=slide.id,
                script=script,
                must_say=_speech(slide.takeaway or slide.title),
                duration_seconds=max(MIN_SECONDS, int(len(script) / CHARS_PER_SECOND)),
            )
        )
    return scripts


def build_rehearsal_cards(deck: SlideDeck, qa: list[QAItem]) -> list[RehearsalCard]:
    """근거로 답하지 못한 질문을 우선 카드로 만든다 — 보강이 필요한 지점이기 때문."""
    cards: list[RehearsalCard] = []
    weak = [item for item in qa if item.answer.startswith(_UNVERIFIED_PREFIX)]
    strong = [item for item in qa if not item.answer.startswith(_UNVERIFIED_PREFIX)]

    def slide_for(index: int) -> str:
        if not deck.slides:
            return ""
        return deck.slides[max(0, min(index, len(deck.slides) - 1))].id

    for index, item in enumerate(weak[:2]):
        cards.append(
            RehearsalCard(
                question=item.question,
                why="원문에 근거가 없어 현재 자료로는 답할 수 없습니다. 답변할 자료를 미리 준비하세요.",
                recommended_slide=slide_for(len(deck.slides) - 1 - index),
            )
        )

    for index, item in enumerate(strong[:1]):
        cards.append(
            RehearsalCard(
                question=item.question,
                why="이 청중이 가장 먼저 묻는 질문입니다. 해당 슬라이드에서 미리 짚어 주세요.",
                recommended_slide=slide_for(index + 1),
            )
        )

    return cards


def support_heuristic(
    deck: SlideDeck,
    content: AudienceContent,
    analysis: SourceAnalysis,
    request: PresentationRequest,
) -> PresentationSupport:
    qa = build_qa_heuristic(analysis, request)
    return PresentationSupport(
        scripts=build_scripts_heuristic(deck, content, request, analysis),
        qa=qa,
        rehearsal_cards=build_rehearsal_cards(deck, qa),
    )


def build_support(
    deck: SlideDeck,
    content: AudienceContent,
    analysis: SourceAnalysis,
    request: PresentationRequest,
    ctx: RunContext,
) -> PresentationSupport:
    """모듈 D 진입점."""
    payload = ctx.call_json(
        stage=STAGE,
        system=support_prompt.SYSTEM,
        user=support_prompt.build_user_prompt(deck, content, analysis, request),
        max_tokens=3500,
    )

    support: PresentationSupport | None = None
    if payload is not None:
        try:
            for item in payload.get("qa", []):
                item.setdefault("asked_by", request.audience.value)
            support = PresentationSupport(**payload)
        except Exception as exc:  # noqa: BLE001
            ctx.note_fallback(STAGE, f"LLM 응답이 계약과 맞지 않습니다: {exc}")
            support = None

    if support is None or not support.scripts:
        return support_heuristic(deck, content, analysis, request)

    known = {e.id for e in analysis.source_evidence}
    slide_ids = {slide.id for slide in deck.slides}

    for item in support.qa:
        item.source_refs = valid_refs(item.source_refs, known)
        if not item.source_refs and not item.answer.startswith(_UNVERIFIED_PREFIX):
            item.answer = f"{_UNVERIFIED_PREFIX}: 답변의 원문 근거를 확인하지 못했습니다. ({item.answer})"

    support.scripts = [s for s in support.scripts if s.slide_id in slide_ids]
    if not support.scripts:
        support.scripts = build_scripts_heuristic(deck, content, request, analysis)
    if not support.qa:
        support.qa = build_qa_heuristic(analysis, request)
    if not support.rehearsal_cards:
        support.rehearsal_cards = build_rehearsal_cards(deck, support.qa)

    return support
