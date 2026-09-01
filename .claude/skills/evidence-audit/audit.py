"""생성 결과 JSON의 원문 근거 무결성을 감사한다.

사용:
    backend\\.venv\\Scripts\\python.exe .claude\\skills\\evidence-audit\\audit.py result.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*\s*(?:%|퍼센트|배|초|분|시간|일|개|건|원|만원|억|GB|MB|ms|s)?")


def collect_slide_text(slide: dict) -> str:
    parts = [slide.get("title", ""), slide.get("takeaway", ""), slide.get("speaker_notes", "")]
    parts.extend(slide.get("bullets", []) or [])
    return " ".join(p for p in parts if p)


def main() -> int:
    if len(sys.argv) < 2:
        print("사용법: audit.py <결과JSON경로>")
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"[오류] 파일을 찾을 수 없습니다: {path}")
        return 2

    data = json.loads(path.read_text(encoding="utf-8"))
    analysis = data.get("source_analysis") or {}
    deck = data.get("slide_deck") or {}
    support = data.get("presentation_support") or {}

    evidence = {e["id"]: e for e in analysis.get("source_evidence", []) if "id" in e}
    slides = deck.get("slides", [])

    failures: list[str] = []
    warnings: list[str] = []

    if not evidence:
        failures.append("source_analysis.source_evidence 가 비어 있습니다. 근거 추적이 불가능합니다.")
    if not slides:
        failures.append("slide_deck.slides 가 비어 있습니다.")

    # 1) 근거 보유 + 2) 근거 유효성
    for slide in slides:
        sid = slide.get("id", "?")
        refs = slide.get("source_refs") or []
        if not refs:
            failures.append(f"{sid}: source_refs 없음 (데모 성공 기준 4번 위반)")
            continue
        unknown = [r for r in refs if r not in evidence]
        if unknown:
            failures.append(f"{sid}: 존재하지 않는 근거 id -> {', '.join(unknown)}")

    # 3) 숫자 대조
    all_source_text = " ".join(e.get("text", "") for e in evidence.values())
    source_numbers = {n.strip() for n in NUMBER_RE.findall(all_source_text) if n.strip()}
    source_digits = {re.sub(r"[^\d.]", "", n) for n in source_numbers}
    source_digits.discard("")

    def check_numbers(label: str, text: str) -> None:
        for token in NUMBER_RE.findall(text):
            digits = re.sub(r"[^\d.]", "", token)
            if not digits or len(digits) < 2:
                continue  # 한 자리 숫자는 목록 번호일 가능성이 높아 제외
            if digits not in source_digits:
                warnings.append(f"{label}: 원문에서 확인되지 않는 숫자 '{token.strip()}'")

    for slide in slides:
        check_numbers(slide.get("id", "?"), collect_slide_text(slide))
    for script in support.get("scripts", []) or []:
        check_numbers(f"script/{script.get('slide_id', '?')}", script.get("script", ""))

    # 4) 미검증 항목
    unverified = analysis.get("unverified") or []

    print(f"슬라이드 {len(slides)}장 / 근거 chunk {len(evidence)}개 검사")
    if unverified:
        print(f"\n[미검증 {len(unverified)}건] 근거를 찾지 못해 표시된 항목 (실패 아님):")
        for u in unverified:
            print(f"  - {u}")
    if warnings:
        print(f"\n[주의 {len(warnings)}건] verifier 가 number_error 로 잡아야 할 후보:")
        for w in warnings:
            print(f"  - {w}")
    if failures:
        print(f"\n[실패 {len(failures)}건]")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("\n[통과] 모든 슬라이드가 유효한 원문 근거를 가지고 있습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
