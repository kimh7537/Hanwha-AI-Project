"""최종 데모 성공 기준 7항목을 mock provider 로 실행 검증한다.

사용:
    backend\\.venv\\Scripts\\python.exe .claude\\skills\\demo-check\\run_demo.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
OUT = Path(__file__).resolve().parent / "out"

os.environ.setdefault("LLM_PROVIDER", "mock")
sys.path.insert(0, str(BACKEND))


def fail(message: str) -> int:
    print(f"\n[중단] {message}")
    print("파이프라인이 아직 구현되지 않았다면 frontend-integrator 서브에이전트에 위임하세요.")
    return 2


def main() -> int:
    sample = BACKEND / "fixtures" / "sample_document.txt"
    if not sample.exists():
        return fail(f"샘플 문서가 없습니다: {sample.relative_to(ROOT)} (doc-analyzer 담당)")

    try:
        from app.models.contracts import PresentationRequest  # type: ignore
        from app.services.pipeline import run_pipeline  # type: ignore
    except Exception as exc:  # noqa: BLE001 - 구현 전 단계에서도 안내가 필요
        return fail(f"파이프라인을 불러오지 못했습니다: {exc}")

    OUT.mkdir(parents=True, exist_ok=True)
    text = sample.read_text(encoding="utf-8")

    def run(audience: str) -> dict:
        request = PresentationRequest(
            audience=audience,
            purpose="technical_explanation",
            duration_minutes=5,
            keywords=["정확도", "도입 효과"],
            style="persuasive",
            preserve_original_terms=True,
            slide_count=5,
        )
        result = run_pipeline(text=text, filename=sample.name, request=request)
        payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else dict(result)
        (OUT / f"{audience}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return payload

    customer = run("customer")
    newcomer = run("newcomer")

    checks: list[tuple[int, str, bool, str]] = []

    analysis = customer.get("source_analysis") or {}
    evidence = analysis.get("source_evidence") or []
    checks.append((1, "기술문서 업로드/파싱", len(evidence) >= 1, f"chunk {len(evidence)}개"))

    checks.append((2, "고객/기술설명/5분/설득형 실행", bool(customer), "파이프라인 완주"))

    slides = (customer.get("slide_deck") or {}).get("slides") or []
    checks.append((3, "5장 안팎 생성", 4 <= len(slides) <= 6, f"{len(slides)}장"))

    no_ref = [s.get("id", "?") for s in slides if not (s.get("source_refs") or [])]
    checks.append(
        (4, "모든 슬라이드에 원문 근거", not no_ref and bool(slides),
         "전부 보유" if not no_ref else f"누락: {', '.join(no_ref)}")
    )

    support = customer.get("presentation_support") or {}
    scripts = support.get("scripts") or []
    qa = support.get("qa") or []
    checks.append(
        (5, "스크립트·Q&A 생성", len(scripts) == len(slides) and 3 <= len(qa) <= 5,
         f"스크립트 {len(scripts)} / Q&A {len(qa)}")
    )

    report = customer.get("verification_report") or {}
    status = report.get("status")
    checks.append(
        (6, "검증 결과 설명 가능", status in {"ok", "warning", "review_needed"} and bool(report.get("summary")),
         f"status={status} summary={'있음' if report.get('summary') else '없음'}")
    )

    def glossary_size(payload: dict) -> int:
        return len((payload.get("audience_content") or {}).get("glossary") or [])

    def deck_text(payload: dict) -> str:
        return json.dumps(payload.get("slide_deck") or {}, ensure_ascii=False)

    differs = glossary_size(newcomer) != glossary_size(customer) or deck_text(newcomer) != deck_text(customer)
    checks.append(
        (7, "신입사원과 결과 차이", differs,
         f"glossary 고객 {glossary_size(customer)} / 신입 {glossary_size(newcomer)}")
    )

    print("데모 성공 기준 검사 결과\n" + "-" * 46)
    failed = 0
    for num, name, ok, detail in checks:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"[{mark}] {num}. {name} — {detail}")

    print("-" * 46)
    print(f"통과 {len(checks) - failed}/{len(checks)}  ·  결과 저장: {OUT.relative_to(ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
