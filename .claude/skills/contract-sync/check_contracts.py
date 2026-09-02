"""Pydantic 모델 · TypeScript 타입 · fixture 사이의 필드 이름 불일치를 찾는다.

정적 텍스트 비교이므로 완벽한 타입 검사는 아니다. 목적은 "한쪽만 고쳤다"를 빠르게 잡는 것.

사용:
    backend\\.venv\\Scripts\\python.exe .claude\\skills\\contract-sync\\check_contracts.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PY_CONTRACTS = ROOT / "backend" / "app" / "models" / "contracts.py"
TS_TYPES = ROOT / "frontend" / "lib" / "types.ts"
FIXTURES = ROOT / "backend" / "fixtures"

# 계약 문서에 정의된 모델 <-> TS 인터페이스 이름 매핑
MODELS = [
    "PresentationRequest",
    "SourceAnalysis",
    "AudienceContent",
    "SlideDeck",
    "Slide",
    "PresentationSupport",
    "VerificationReport",
]

PY_CLASS_RE = r"class\s+{name}\s*\([^)]*\)\s*:(?P<body>.*?)(?=\nclass\s|\Z)"
PY_FIELD_RE = re.compile(r"^\s{4}(?P<field>[a-z_][a-z0-9_]*)\s*:", re.MULTILINE)
TS_IFACE_RE = r"(?:export\s+)?(?:interface|type)\s+{name}\s*(?:=\s*)?\{{(?P<body>.*?)\n\}}"
TS_FIELD_RE = re.compile(r"^\s{2}(?P<field>[A-Za-z_][A-Za-z0-9_]*)\??\s*:", re.MULTILINE)


def extract(text: str, pattern: str, field_re: re.Pattern, name: str) -> set[str] | None:
    match = re.search(pattern.format(name=name), text, re.DOTALL)
    if not match:
        return None
    return set(field_re.findall(match.group("body")))


def main() -> int:
    problems: list[str] = []
    notes: list[str] = []

    if not PY_CONTRACTS.exists():
        notes.append(f"아직 없음: {PY_CONTRACTS.relative_to(ROOT)}")
    if not TS_TYPES.exists():
        notes.append(f"아직 없음: {TS_TYPES.relative_to(ROOT)}")

    if PY_CONTRACTS.exists() and TS_TYPES.exists():
        py_text = PY_CONTRACTS.read_text(encoding="utf-8")
        ts_text = TS_TYPES.read_text(encoding="utf-8")

        for name in MODELS:
            py_fields = extract(py_text, PY_CLASS_RE, PY_FIELD_RE, name)
            ts_fields = extract(ts_text, TS_IFACE_RE, TS_FIELD_RE, name)

            if py_fields is None and ts_fields is None:
                notes.append(f"{name}: 양쪽 모두 미정의 (아직 구현 전)")
                continue
            if py_fields is None:
                problems.append(f"{name}: Pydantic 모델 없음 (TS에만 존재)")
                continue
            if ts_fields is None:
                problems.append(f"{name}: TypeScript 타입 없음 (Pydantic에만 존재)")
                continue

            only_py = sorted(py_fields - ts_fields)
            only_ts = sorted(ts_fields - py_fields)
            if only_py:
                problems.append(f"{name}: Pydantic에만 있는 필드 -> {', '.join(only_py)}")
            if only_ts:
                problems.append(f"{name}: TypeScript에만 있는 필드 -> {', '.join(only_ts)}")

    # fixture 는 최소한 JSON 으로 파싱되어야 한다
    if FIXTURES.exists():
        for path in sorted(FIXTURES.glob("*.json")):
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                problems.append(f"fixture 파싱 실패 {path.name}: {exc}")
    else:
        notes.append("아직 없음: backend/fixtures/")

    for note in notes:
        print(f"[정보] {note}")

    if problems:
        print("\n[불일치] 계약 동기화가 필요합니다:")
        for p in problems:
            print(f"  - {p}")
        print("\n-> docs/01-contracts.md 를 기준으로 4곳(Pydantic/TS/fixture/문서)을 함께 고치세요.")
        return 1

    print("[정상] 계약 불일치를 찾지 못했습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
