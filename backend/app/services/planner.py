"""모듈 C: AudienceContent -> SlideDeck (docs/04-slide-planner.md).

모든 슬라이드는 원문 근거를 1개 이상 가진다. 근거를 만들 수 없는 내용은 슬라이드로 만들지 않는다.
"""

from __future__ import annotations

from app.llm.base import RunContext
from app.models.contracts import (
    Audience,
    AudienceContent,
    PresentationRequest,
    Purpose,
    Slide,
    SlideDeck,
    SourceAnalysis,
)
from app.prompts import planner as planner_prompt
from app.services import textutil
from app.services.evidence import inherit_refs, valid_refs

STAGE = "슬라이드 설계"

MIN_SLIDES = 3
MAX_SLIDES = 10

# 발표 시간별 기본 장수 (docs/04-slide-planner.md)
_DURATION_SLIDES = {3: 4, 5: 5, 10: 7}

_PURPOSE_TITLES: dict[Purpose, str] = {
    Purpose.EDUCATION: "교육 자료",
    Purpose.INTERNAL_REPORT: "내부 보고",
    Purpose.TECHNICAL_EXPLANATION: "기술 설명",
    Purpose.PROPOSAL: "제안",
}

_VISUALS = {
    "무엇을 하는 기술인가": "한 문장 핵심 메시지 + 시스템 아이콘",
    "왜 필요한가": "현재 소요 시간 vs 목표를 대비한 막대 그래프",
    "어떻게 동작하나": "입력 → 처리 → 출력 3단계 흐름도",
    "기술 구성": "구성 요소 블록 다이어그램",
    "성능과 측정 조건": "핵심 지표 카드 3개",
    "적용 조건과 제약": "체크리스트 형태의 조건 목록",
    "결론": "핵심 결론 한 줄 + 다음 행동",
    "도입 효과": "Before / After 비교 표",
    "리스크와 전제 조건": "리스크 항목과 대응을 짝지은 표",
    "판단에 필요한 기술 요약": "핵심 구조 요약 다이어그램",
    "제공하는 가치": "고객 가치 3가지 아이콘 카드",
    "적용 효과": "Before / After 비교 표",
    "동작 방식": "입력 → 처리 → 출력 흐름도",
    "적용 전 확인이 필요한 조건": "전제 조건 체크리스트",
}


def resolve_slide_count(request: PresentationRequest) -> int:
    count = request.slide_count or _DURATION_SLIDES.get(request.duration_minutes, 5)
    return max(MIN_SLIDES, min(MAX_SLIDES, count))


def _bullets_from_text(text: str, limit: int = 4) -> list[str]:
    """설명 문단을 bullet 목록으로. 문장 단위로 나누되 문장을 잘라 조각내지 않는다.

    명세의 '40자 내외'는 LLM 이 의미를 압축했을 때의 기준이다. 휴리스틱 경로는 의미 압축을
    할 수 없으므로, 문장을 어중간하게 자르는 대신 한 문장을 그대로 쓴다.
    """
    sentences = textutil.split_sentences(text) or [text]
    bullets: list[str] = []
    for sentence in sentences:
        bullet = textutil.to_bullet(sentence)
        if bullet and bullet not in bullets:
            bullets.append(bullet)
        if len(bullets) >= limit:
            break
    return bullets


def _takeaway(text: str) -> str:
    """슬라이드 결론 한 문장. 화면에 그대로 읽히므로 말줄임표를 남기지 않는다."""
    return textutil.first_sentence(text, 100)


def plan_heuristic(
    content: AudienceContent, analysis: SourceAnalysis, request: PresentationRequest
) -> SlideDeck:
    target = resolve_slide_count(request)

    # 1) 청중용 설명 하나당 슬라이드 하나를 만든다
    blocks: list[Slide] = []
    seen_takeaways: set[str] = set()

    for explanation in content.explanations:
        if not explanation.source_refs:
            continue  # 근거 없는 내용은 슬라이드로 만들지 않는다

        takeaway = _takeaway(explanation.text)
        if takeaway in seen_takeaways:
            continue  # 같은 결론을 두 장에 반복하지 않는다
        seen_takeaways.add(takeaway)

        blocks.append(
            Slide(
                id="",
                title=explanation.topic,
                takeaway=takeaway,
                bullets=_bullets_from_text(explanation.text),
                visual_suggestion=_VISUALS.get(explanation.topic, "핵심 내용을 도식으로 정리"),
                # 모듈 D 가 스크립트로 확장할 씨앗. 자르지 않고 문장 전체를 넘긴다.
                speaker_notes=explanation.text,
                source_refs=list(explanation.source_refs),
            )
        )

    # 2) 결론 슬라이드는 앞 슬라이드의 근거를 승계한다
    conclusion_refs = inherit_refs(*[b.source_refs for b in blocks])
    if conclusion_refs:
        blocks.append(
            Slide(
                id="",
                title="결론 및 다음 행동",
                takeaway=_conclusion_takeaway(analysis, content, seen_takeaways),
                bullets=_conclusion_bullets(analysis, content),
                visual_suggestion=_VISUALS["결론"],
                speaker_notes="핵심 메시지를 다시 강조하고 다음 행동을 요청한다.",
                source_refs=conclusion_refs[:3],
            )
        )

    # 3) 장수 맞추기
    if len(blocks) > target:
        # 3분 발표는 결론 우선. 마지막(결론)을 남기고 중간을 덜어낸다.
        conclusion = blocks[-1]
        body = blocks[:-1]
        if request.duration_minutes == 3:
            blocks = [conclusion] + body[: target - 1]
        else:
            blocks = body[: target - 1] + [conclusion]
    elif len(blocks) < target:
        blocks.extend(_extra_slides(analysis, target - len(blocks)))

    # 4) id 부여 및 근거 보증
    slides: list[Slide] = []
    for index, slide in enumerate(blocks[:target], start=1):
        slide.id = f"slide-{index}"
        if not slide.bullets:
            slide.bullets = [textutil.to_bullet(slide.takeaway)]
        slides.append(slide)

    deck = SlideDeck(
        title=_deck_title(analysis, request),
        slides=slides,
    )
    _ensure_keywords(deck, analysis, request)
    return deck


def _conclusion_takeaway(
    analysis: SourceAnalysis, content: AudienceContent, used: set[str]
) -> str:
    """결론 슬라이드의 한 문장.

    핵심 메시지를 쓰되, 첫 슬라이드가 이미 같은 문장을 쓰고 있으면 같은 결론을 두 번 보여주는
    셈이므로 도입 효과 문장으로 대신한다.
    """
    candidates = [analysis.core_message]
    candidates.extend(
        number.meaning
        for number in sorted(
            analysis.numbers, key=lambda n: textutil.effect_strength(n.meaning), reverse=True
        )
        if textutil.effect_strength(number.meaning) > 0
    )
    candidates.extend(content.emphasis)

    for candidate in candidates:
        takeaway = _takeaway(candidate)
        if takeaway and takeaway not in used:
            used.add(takeaway)
            return takeaway

    return _takeaway(analysis.core_message)


def _conclusion_bullets(analysis: SourceAnalysis, content: AudienceContent) -> list[str]:
    """결론 bullet 은 원문 사실을 우선한다. 일반적인 문구는 채울 게 없을 때만 쓴다."""
    bullets: list[str] = []

    def add(text: str) -> None:
        bullet = textutil.to_bullet(text, 70)
        # 같은 문장에서 뽑힌 수치가 여러 개면 bullet 이 중복된다
        if bullet and bullet not in bullets:
            bullets.append(bullet)

    effects = sorted(analysis.numbers, key=lambda n: textutil.effect_strength(n.meaning), reverse=True)
    for number in effects:
        if textutil.effect_strength(number.meaning) <= 0 or len(bullets) >= 2:
            break
        add(number.meaning)

    for condition in analysis.must_keep[:1]:
        add(condition.text)

    for point in content.emphasis:
        if len(bullets) >= 3:
            break
        add(point)

    return bullets[:3]


def _deck_title(analysis: SourceAnalysis, request: PresentationRequest) -> str:
    """덱 제목. 문서 자체의 제목 줄이 있으면 그것을 쓰는 편이 자연스럽다."""
    subject = ""

    if analysis.source_evidence:
        for line in analysis.source_evidence[0].text.splitlines():
            candidate = textutil.normalize(line)
            if 4 <= len(candidate) <= 40:
                subject = candidate
                break

    if not subject:
        subject = textutil.clip_clause(analysis.core_message, 40) or "기술 발표"

    return f"{subject} — {_PURPOSE_TITLES.get(request.purpose, '발표')}"


def _extra_slides(analysis: SourceAnalysis, needed: int) -> list[Slide]:
    """장수가 모자랄 때 원문 사실로 슬라이드를 보충한다."""
    extras: list[Slide] = []

    if analysis.numbers and needed > 0:
        numbers = analysis.numbers[:4]
        extras.append(
            Slide(
                id="",
                title="핵심 수치",
                takeaway="원문에서 확인된 수치입니다.",
                bullets=[f"{n.value}{n.unit} — {textutil.to_bullet(n.meaning, 34)}" for n in numbers],
                visual_suggestion="핵심 지표 카드",
                speaker_notes="수치는 모두 원문 근거와 연결되어 있다.",
                source_refs=inherit_refs(*[n.source_refs for n in numbers]),
            )
        )

    if analysis.must_keep and len(extras) < needed:
        conditions = analysis.must_keep[:4]
        extras.append(
            Slide(
                id="",
                title="반드시 지켜야 할 조건",
                takeaway="적용 전 확인이 필요한 조건입니다.",
                bullets=[textutil.to_bullet(c.text) for c in conditions],
                visual_suggestion="조건 체크리스트",
                speaker_notes="이 조건이 빠지면 원문을 과도하게 단순화한 것이 된다.",
                source_refs=inherit_refs(*[c.source_refs for c in conditions]),
            )
        )

    if analysis.terms and len(extras) < needed:
        terms = analysis.terms[:4]
        extras.append(
            Slide(
                id="",
                title="용어 정리",
                takeaway="발표에 나오는 용어를 먼저 정리합니다.",
                bullets=[f"{t.term}: {textutil.to_bullet(t.definition, 30)}" for t in terms],
                visual_suggestion="용어와 뜻을 나란히 둔 표",
                speaker_notes="청중이 모를 수 있는 용어를 먼저 설명한다.",
                source_refs=inherit_refs(*[t.source_refs for t in terms]),
            )
        )

    return [slide for slide in extras if slide.source_refs][:needed]


def _ensure_keywords(
    deck: SlideDeck, analysis: SourceAnalysis, request: PresentationRequest
) -> None:
    """필수 키워드가 덱에 없으면 원문 문장을 근거와 함께 보강한다."""
    if not deck.slides:
        return

    deck_text = " ".join(
        " ".join([slide.title, slide.takeaway, *slide.bullets]) for slide in deck.slides
    )

    for keyword in request.keywords:
        if not keyword or keyword in deck_text:
            continue

        supporting = _find_keyword_evidence(analysis, keyword)
        if supporting is None:
            continue  # 원문에 없는 키워드다. 검증 모듈이 omission 으로 보고한다.

        sentence, evidence_id = supporting

        # 같은 근거를 이미 인용하고 있는 슬라이드에 붙인다. 주제가 맞는 자리이기 때문.
        target = next(
            (slide for slide in deck.slides if evidence_id in slide.source_refs),
            deck.slides[min(1, len(deck.slides) - 1)],
        )

        # 키워드가 섹션 제목에만 있었다면 문장에는 키워드가 없다.
        # 그대로 넣으면 키워드가 여전히 덱에 등장하지 않으므로 앞에 붙여 준다.
        body = textutil.to_bullet(sentence, 70)

        # 이미 같은 내용을 담은 bullet 이 있으면 새로 추가하지 않고 거기에 키워드를 붙인다.
        existing = _matching_bullet(target.bullets, body)
        if existing is not None:
            if keyword not in target.bullets[existing]:
                target.bullets[existing] = f"{keyword}: {target.bullets[existing]}"
            target.source_refs = inherit_refs(target.source_refs, [evidence_id])
            continue

        bullet = body if keyword in sentence else f"{keyword}: {body}"
        target.bullets.append(bullet)
        target.source_refs = inherit_refs(target.source_refs, [evidence_id])


def _matching_bullet(bullets: list[str], candidate: str) -> int | None:
    """같은 내용을 담은 bullet 의 위치. 없으면 None."""
    tokens = set(textutil.tokenize(candidate))
    if not tokens:
        return None
    for index, bullet in enumerate(bullets):
        bullet_tokens = set(textutil.tokenize(bullet))
        if bullet_tokens and len(tokens & bullet_tokens) / len(tokens) >= 0.6:
            return index
    return None


def _find_keyword_evidence(
    analysis: SourceAnalysis, keyword: str
) -> tuple[str, str] | None:
    """키워드를 담은 원문 문장을 찾는다.

    키워드가 '5. 도입 효과' 처럼 섹션 제목에만 있는 경우가 있다. 제목은 발표 문장으로 쓸 수 없으므로
    그 제목 다음에 오는 본문 문장을 근거 문장으로 사용한다.
    """
    for evidence in analysis.source_evidence:
        position = evidence.text.find(keyword)
        if position == -1:
            continue

        sentences = textutil.split_sentences(evidence.text)
        cursor = 0
        after_keyword: str | None = None

        for sentence in sentences:
            found = evidence.text.find(sentence[:12], cursor)
            if found == -1:
                found = cursor
            cursor = found + 1

            if keyword in sentence:
                return sentence, evidence.id
            if after_keyword is None and found > position and len(sentence) >= 20:
                after_keyword = sentence

        if after_keyword:
            return after_keyword, evidence.id

    return None


def plan(
    content: AudienceContent,
    analysis: SourceAnalysis,
    request: PresentationRequest,
    ctx: RunContext,
) -> SlideDeck:
    """모듈 C 진입점."""
    target = resolve_slide_count(request)

    payload = ctx.call_json(
        stage=STAGE,
        system=planner_prompt.SYSTEM,
        user=planner_prompt.build_user_prompt(content, analysis, request, target),
        max_tokens=3000,
    )

    deck: SlideDeck | None = None
    if payload is not None:
        try:
            deck = SlideDeck(**payload)
        except Exception as exc:  # noqa: BLE001
            ctx.note_fallback(STAGE, f"LLM 응답이 계약과 맞지 않습니다: {exc}")
            deck = None

    if deck is None or not deck.slides:
        return plan_heuristic(content, analysis, request)

    known = {e.id for e in analysis.source_evidence}
    kept: list[Slide] = []
    for index, slide in enumerate(deck.slides, start=1):
        slide.source_refs = valid_refs(slide.source_refs, known)
        slide.id = f"slide-{index}"
        if slide.source_refs:
            kept.append(slide)
        else:
            ctx.note_fallback(STAGE, f"{slide.title or slide.id}: 근거가 없어 슬라이드에서 제외했습니다.")

    if not kept:
        return plan_heuristic(content, analysis, request)

    for index, slide in enumerate(kept, start=1):
        slide.id = f"slide-{index}"

    deck.slides = kept
    if not deck.title:
        deck.title = _deck_title(analysis, request)
    _ensure_keywords(deck, analysis, request)
    return deck
