"""샘플 문서로 파이프라인을 돌려 모듈별 fixture JSON 을 갱신한다.

계약(docs/01-contracts.md)이 바뀌면 이 스크립트를 다시 돌려 fixture 를 맞춘다.

사용:
    backend\\.venv\\Scripts\\python.exe backend\\scripts\\build_fixtures.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("LLM_PROVIDER", "mock")

from app.models.contracts import PresentationRequest  # noqa: E402
from app.services.pipeline import run_pipeline  # noqa: E402

FIXTURES = BACKEND / "fixtures"

REQUEST = PresentationRequest(
    audience="customer",
    purpose="technical_explanation",
    duration_minutes=5,
    keywords=["정확도", "도입 효과"],
    style="persuasive",
    preserve_original_terms=True,
    slide_count=5,
)


def write(name: str, payload: object) -> None:
    path = FIXTURES / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  갱신: fixtures/{name}")


def main() -> int:
    sample = FIXTURES / "sample_document.txt"
    if not sample.exists():
        print(f"[오류] 샘플 문서가 없습니다: {sample}")
        return 1

    result = run_pipeline(
        text=sample.read_text(encoding="utf-8"),
        filename=sample.name,
        request=REQUEST,
    )

    print("fixture 를 갱신합니다 (provider=mock)")
    write("presentation_request.json", REQUEST.model_dump(mode="json"))
    write("source_analysis.json", result.source_analysis.model_dump(mode="json"))
    write("audience_content.json", result.audience_content.model_dump(mode="json"))
    write("slide_deck.json", result.slide_deck.model_dump(mode="json"))
    write("presentation_support.json", result.presentation_support.model_dump(mode="json"))
    if result.verification_report:
        write("verification_report.json", result.verification_report.model_dump(mode="json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
