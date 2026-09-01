"""모듈 A: 원문 -> SourceAnalysis (docs/02-document-analysis.md).

LLM 이 있으면 LLM 으로, 없거나 실패하면 규칙 기반 휴리스틱으로 같은 계약을 만든다.
어느 경로든 마지막에 근거 무결성을 강제한다.
"""

from __future__ import annotations

import re

from app.config import get_settings
from app.llm.base import RunContext
from app.models.contracts import (
    Chunk,
    EvidenceItem,
    NumberFact,
    PresentationRequest,
    SourceAnalysis,
    SourceEvidence,
    TermFact,
)
from app.prompts import analysis as analysis_prompt
from app.services import retrieval, textutil
from app.services.evidence import enforce_analysis_evidence

STAGE = "문서 분석"

# 기술 서술을 담은 문장을 고르는 표지
_TECHNICAL_MARKERS = (
    "동작", "구조", "방식", "단계", "모듈", "기반", "사용한다", "변환", "처리",
    "분류", "지원한다", "구성", "우선한다", "적용",
)

# "임베딩(embedding, 문장을 숫자 벡터로 바꾼 표현)" 형태 - 괄호 바로 앞 한 낱말만 용어로 본다
_TERM_PAREN = re.compile(r"([가-힣A-Za-z0-9]{2,20})\(([A-Za-z][A-Za-z0-9 \-]{1,24}),\s*([^)]{4,80})\)")
# "F1 점수는 정밀도와 재현율의 조화평균으로 ..." 형태
_TERM_DEFINE = re.compile(r"^([A-Za-z0-9가-힣]{2,12}(?:\s[A-Za-z0-9가-힣]{1,8})?)(?:는|은|이란|란)\s+(.{10,90})$")

# 정의문임을 알려주는 표지. 이게 없으면 그냥 서술문이므로 용어로 보지 않는다.
_DEFINITION_MARKERS = (
    "이다", "말한다", "의미한다", "가리킨다", "방식", "표현", "지표", "평균",
    "구조", "값", "개념", "기법", "단위",
)

# 용어 후보에서 걸러낼 어미 조각 (문장을 잘못 자른 결과)
_TERM_REJECT_SUFFIX = ("없", "않", "되", "하", "있", "인", "한", "된", "을", "를", "이", "가")


def _sentences_with_refs(chunks: list[Chunk]) -> list[tuple[str, str]]:
    """(문장, chunk id) 목록."""
    pairs: list[tuple[str, str]] = []
    for chunk in chunks:
        for sentence in textutil.split_sentences(chunk.text):
            pairs.append((sentence, chunk.id))
    return pairs


def _pick_core_message(pairs: list[tuple[str, str]], keywords: list[str]) -> tuple[str, list[str]]:
    best_score = -1.0
    best: tuple[str, str] | None = None
    for sentence, ref in pairs:
        score = float(textutil.keyword_overlap(sentence, keywords)) * 3.0
        if re.search(r"(시스템|서비스|플랫폼|도구)(이다|다|입니다)", sentence):
            score += 4.0
        if "이다" in sentence or "한다" in sentence:
            score += 1.0
        if 20 <= len(sentence) <= 120:
            score += 1.5
        if score > best_score:
            best_score, best = score, (sentence, ref)
    if not best:
        return "", []
    return best[0], [best[1]]


def _collect_numbers(chunks: list[Chunk]) -> list[NumberFact]:
    facts: list[NumberFact] = []
    seen: set[tuple[str, str]] = set()
    for chunk in chunks:
        for sentence in textutil.split_sentences(chunk.text):
            for value, unit in textutil.extract_numbers(sentence):
                key = (textutil.number_key(value), unit)
                if key in seen:
                    continue
                seen.add(key)
                facts.append(
                    NumberFact(
                        value=value,
                        unit=unit,
                        meaning=textutil.shorten(sentence, 90),
                        source_refs=[chunk.id],
                    )
                )
    return facts


def _collect_terms(chunks: list[Chunk]) -> list[TermFact]:
    terms: list[TermFact] = []
    seen: set[str] = set()

    def add(term: str, definition: str, ref: str) -> None:
        key = term.strip()
        if not key or key in seen or len(key) > 24:
            return
        seen.add(key)
        terms.append(
            TermFact(term=key, definition=textutil.shorten(definition, 100), source_refs=[ref])
        )

    for chunk in chunks:
        for match in _TERM_PAREN.finditer(chunk.text):
            korean, english, definition = match.groups()
            add(f"{korean.strip()}({english.strip()})", definition, chunk.id)

        for sentence in textutil.split_sentences(chunk.text):
            match = _TERM_DEFINE.match(sentence)
            if not match:
                continue
            term, definition = match.group(1).strip(), match.group(2)
            # 지시어로 시작하거나 어미 조각인 후보, 정의문이 아닌 서술문은 버린다
            if term.startswith(("이", "그", "저")) or term.endswith(_TERM_REJECT_SUFFIX):
                continue
            if not textutil.contains_any(definition, _DEFINITION_MARKERS):
                continue
            add(term, definition, chunk.id)
    return terms


def _collect_must_keep(chunks: list[Chunk]) -> list[EvidenceItem]:
    """조건/주의사항 문장. 강한 조건(금지·필수·전제)이 앞에 오도록 정렬한다."""
    scored: list[tuple[int, EvidenceItem]] = []
    seen: set[str] = set()

    for chunk in chunks:
        for sentence in textutil.split_sentences(chunk.text):
            strength = textutil.condition_strength(sentence)
            if strength <= 0:
                continue
            key = textutil.normalize(sentence)
            if key in seen or len(key) < 12:
                continue
            seen.add(key)
            scored.append(
                (strength, EvidenceItem(text=textutil.clip_clause(sentence, 130), source_refs=[chunk.id]))
            )

    scored.sort(key=lambda row: row[0], reverse=True)
    return [item for _, item in scored]


def _collect_key_features(chunks: list[Chunk]) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    seen: set[str] = set()
    for chunk in chunks:
        for bullet in textutil.iter_bullets(chunk.text):
            key = textutil.normalize(bullet)
            if key in seen:
                continue
            seen.add(key)
            items.append(EvidenceItem(text=textutil.shorten(bullet, 150), source_refs=[chunk.id]))
    return items


def _collect_technical_points(
    pairs: list[tuple[str, str]], keywords: list[str], limit: int = 8
) -> list[EvidenceItem]:
    scored: list[tuple[float, str, str]] = []
    for sentence, ref in pairs:
        score = float(len(textutil.contains_any(sentence, _TECHNICAL_MARKERS)))
        score += textutil.keyword_overlap(sentence, keywords) * 2.0
        if score <= 0:
            continue
        if 15 <= len(sentence) <= 140:
            score += 1.0
        scored.append((score, sentence, ref))

    scored.sort(key=lambda row: row[0], reverse=True)
    items: list[EvidenceItem] = []
    seen: set[str] = set()
    for _, sentence, ref in scored:
        key = textutil.normalize(sentence)
        if key in seen:
            continue
        seen.add(key)
        items.append(EvidenceItem(text=textutil.shorten(sentence, 130), source_refs=[ref]))
        if len(items) >= limit:
            break
    return items


def analyze_heuristic(chunks: list[Chunk], request: PresentationRequest) -> SourceAnalysis:
    """LLM 없이 원문에서 사실을 뽑는다. 문장을 지어내지 않고 골라낸다."""
    pairs = _sentences_with_refs(chunks)
    core_message, core_refs = _pick_core_message(pairs, request.keywords)

    analysis = SourceAnalysis(
        core_message=core_message,
        technical_points=_collect_technical_points(pairs, request.keywords),
        key_features=_collect_key_features(chunks),
        numbers=_collect_numbers(chunks),
        terms=_collect_terms(chunks),
        must_keep=_collect_must_keep(chunks),
        source_evidence=[
            SourceEvidence(id=chunk.id, text=chunk.text, page=chunk.page) for chunk in chunks
        ],
    )

    if not core_message:
        analysis.unverified.append("핵심 메시지를 문서에서 특정하지 못했습니다.")
    elif not core_refs:
        analysis.unverified.append("핵심 메시지의 근거 chunk 를 특정하지 못했습니다.")

    missing = [kw for kw in request.keywords if kw and kw not in "\n".join(c.text for c in chunks)]
    for keyword in missing:
        analysis.unverified.append(f"필수 키워드 '{keyword}' 가 원문에 없습니다.")

    return analysis


def _is_substantive(analysis: SourceAnalysis) -> bool:
    """이후 단계가 쓸 수 있는 최소한의 내용이 있는지."""
    return bool(
        analysis.core_message
        or analysis.technical_points
        or analysis.key_features
        or analysis.numbers
    )


def analyze(
    chunks: list[Chunk],
    request: PresentationRequest,
    ctx: RunContext,
    namespace: str = "",
) -> SourceAnalysis:
    """모듈 A 진입점.

    `namespace` 는 Chroma 컬렉션을 문서별로 나누기 위한 식별자(document_id)다.
    """
    if not chunks:
        return SourceAnalysis(unverified=["문서에서 근거를 추출하지 못했습니다."])

    settings = get_settings()

    # LLM 을 쓸 수 없으면 프롬프트를 만들 일도 없다. mock 데모가 네트워크를 타지 않도록
    # 검색 자체를 건너뛴다 (docs/08: 키·Chroma 없이도 전체 데모가 동작해야 한다).
    prompt_chunks = chunks
    if ctx.llm_enabled:
        prompt_chunks = retrieval.select_chunks(
            chunks,
            request.keywords,
            settings.max_prompt_chars,
            namespace=namespace,
            ctx=ctx,
        )

    payload = ctx.call_json(
        stage=STAGE,
        system=analysis_prompt.SYSTEM,
        user=analysis_prompt.build_user_prompt(
            prompt_chunks, request.keywords, settings.max_prompt_chars
        ),
        max_tokens=3000,
    )

    analysis: SourceAnalysis | None = None
    if payload is not None:
        try:
            payload.pop("source_evidence", None)  # 근거 원문은 우리가 채운다
            analysis = SourceAnalysis(**payload)
        except Exception as exc:  # noqa: BLE001
            ctx.note_fallback(STAGE, f"LLM 응답이 계약과 맞지 않습니다: {exc}")
            analysis = None
        else:
            # 계약의 모든 필드에 기본값이 있어서, 형태가 전혀 다른 JSON 도 '빈 분석' 으로 통과한다.
            # 빈 분석을 그대로 흘리면 이후 단계가 전부 비어 버리므로 여기서 걸러 낸다.
            if not _is_substantive(analysis):
                ctx.note_fallback(STAGE, "LLM 응답이 계약과 맞지 않습니다: 추출된 사실이 없습니다")
                analysis = None

    if analysis is None:
        analysis = analyze_heuristic(chunks, request)
    else:
        analysis.source_evidence = [
            SourceEvidence(id=chunk.id, text=chunk.text, page=chunk.page) for chunk in chunks
        ]

    return enforce_analysis_evidence(analysis, chunks)
