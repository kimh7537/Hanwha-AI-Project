"""근거(source_refs) 무결성 강제.

LLM 이 만들어낸 chunk id 든 휴리스틱이 붙인 id 든, 실제 존재하는 chunk 만 남긴다.
근거가 하나도 남지 않은 항목은 삭제하지 않고 unverified 로 옮긴다 (docs/10-quality-safety.md).
"""

from __future__ import annotations

from app.models.contracts import Chunk, SourceAnalysis


def valid_refs(refs: list[str] | None, known_ids: set[str]) -> list[str]:
    seen: set[str] = set()
    kept: list[str] = []
    for ref in refs or []:
        if ref in known_ids and ref not in seen:
            seen.add(ref)
            kept.append(ref)
    return kept


def enforce_analysis_evidence(analysis: SourceAnalysis, chunks: list[Chunk]) -> SourceAnalysis:
    """근거가 유효하지 않은 항목을 걸러 unverified 로 옮긴다."""
    known = {chunk.id for chunk in chunks}
    unverified = list(analysis.unverified)

    def keep_items(items, describe):  # type: ignore[no-untyped-def]
        kept = []
        for item in items:
            item.source_refs = valid_refs(item.source_refs, known)
            if item.source_refs:
                kept.append(item)
            else:
                unverified.append(describe(item))
        return kept

    analysis.technical_points = keep_items(
        analysis.technical_points, lambda i: f"근거 없는 기술 항목: {i.text}"
    )
    analysis.key_features = keep_items(
        analysis.key_features, lambda i: f"근거 없는 특징 항목: {i.text}"
    )
    analysis.must_keep = keep_items(
        analysis.must_keep, lambda i: f"근거 없는 필수 조건: {i.text}"
    )
    analysis.numbers = keep_items(
        analysis.numbers, lambda i: f"근거 없는 수치: {i.value}{i.unit}"
    )
    analysis.terms = keep_items(
        analysis.terms, lambda i: f"근거 없는 용어: {i.term}"
    )

    # 중복 제거하되 순서는 유지
    seen: set[str] = set()
    analysis.unverified = [u for u in unverified if not (u in seen or seen.add(u))]
    return analysis


def inherit_refs(*ref_lists: list[str]) -> list[str]:
    """여러 항목의 근거를 합집합으로 승계한다 (순서 유지)."""
    seen: set[str] = set()
    merged: list[str] = []
    for refs in ref_lists:
        for ref in refs or []:
            if ref not in seen:
                seen.add(ref)
                merged.append(ref)
    return merged
