---
name: demo-check
description: 최종 데모 성공 기준 7항목을 실제로 실행해 검증한다. 파이프라인을 mock provider로 끝까지 돌려 고객/기술설명/5분/설득형 결과와 신입사원 결과를 비교한다. 데모 리허설 전, Day 4 시연 안정화 중, 또는 "지금 어디까지 됐나" 확인할 때 사용한다.
---

# 데모 성공 기준 검사

`docs/09-schedule-and-demo.md`의 7항목을 **주장이 아니라 실행으로** 확인한다.

## 실행

```powershell
backend\.venv\Scripts\python.exe .claude\skills\demo-check\run_demo.py
```

이 스크립트는 백엔드 서버 없이 파이프라인 함수를 직접 호출하며 `LLM_PROVIDER=mock`으로 고정한다.
API 키 없이도 항상 돌아가야 한다 — 돌아가지 않으면 그 자체가 결함이다.

결과 JSON은 `.claude/skills/demo-check/out/`에 저장되므로 이어서 감사할 수 있다.

```powershell
backend\.venv\Scripts\python.exe .claude\skills\evidence-audit\audit.py .claude\skills\demo-check\out\customer.json
```

## 검사하는 7항목

| # | 기준 | 판정 방법 |
|---|---|---|
| 1 | 기술문서 업로드 | `backend/fixtures/sample_document.txt` 파싱 성공, chunk ≥1 |
| 2 | 고객/기술설명/5분/설득형 선택 | 해당 `PresentationRequest`로 파이프라인 실행 |
| 3 | 5장 안팎 생성 | `len(slides)`가 4~6 |
| 4 | 모든 슬라이드에 원문 근거 | 전 슬라이드 `source_refs` 비어있지 않음 |
| 5 | 스크립트·Q&A 생성 | `scripts` 수 = 슬라이드 수, `qa` 3~5개 |
| 6 | 검증 결과 설명 가능 | `status`가 ok/warning이고 `summary`가 비어있지 않음 |
| 7 | 신입사원과 차이 | 같은 문서로 `newcomer` 실행 시 glossary 수·본문이 유의미하게 다름 |

## 실패 시

**어느 모듈의 문제인지 판정한 뒤 해당 서브에이전트에 위임하라.**
1~2번 → `doc-analyzer` / 3~4번 → `slide-planner` / 5번 → `presentation-support` /
6번 → `verifier` / 7번 → `audience-transformer` / 파이프라인 배선 → `frontend-integrator`

**Day 4에는 새 기능을 만들지 말고 실패한 항목만 고친다.**
