---
name: spec-route
description: 기획안의 어느 부분이 이 작업에 해당하는지 찾아 담당 서브에이전트에 위임한다. 요청이 여러 모듈에 걸쳐 있거나, 어떤 문서를 읽어야 할지 모르거나, "기획안대로 만들어줘" 같은 넓은 요청을 받았을 때 가장 먼저 사용한다.
---

# 기획안 라우팅

원본 기획안 `claude-code-implementation-brief.md`는 한 번에 읽기에 길다.
`docs/`에 모듈별로 분해되어 있으므로 **필요한 조각만 읽고 담당 에이전트에 넘긴다.**

## 라우팅 표

| 요청 키워드 | 읽을 문서 | 위임할 서브에이전트 |
|---|---|---|
| 파싱, PDF, chunk, 근거 추출, SourceAnalysis | `docs/02` | `doc-analyzer` |
| 청중, 신입/실무자/임원/고객, 톤, 용어 풀이, 원어 유지 | `docs/03` | `audience-transformer` |
| 슬라이드, 덱 구성, 발표 시간, 장수, PPTX | `docs/04` | `slide-planner` |
| 스크립트, 대본, 예상 질문, Q&A, 리허설 | `docs/05` | `presentation-support` |
| 검증, 근거 대조, 숫자 오류, 왜곡, 민감정보 | `docs/06` | `verifier` |
| UI, 화면, 위저드, 탭, 타입, API 연결, 라우터 | `docs/07`, `docs/08` | `frontend-integrator` |
| 일정, 데모, 완료 조건, 평가표 | `docs/09` | (직접 처리) |
| 환각, 안전, 비밀정보, 오류 메시지 | `docs/10` | (전원 공통) |

`docs/00-overview.md`와 `docs/01-contracts.md`는 **모든 작업의 공통 전제**다.
계약을 건드려야 하면 위임 전에 `/contract-sync`를 먼저 돌려라.

## 위임 절차

1. 요청을 모듈 단위로 쪼갠다. 한 요청이 3개 모듈에 걸치면 3개로 나눈다.
2. **서로 의존하지 않는 모듈은 한 메시지에서 동시에 위임한다.**
   파이프라인 순서(A→B→C→D→E)상 앞 단계의 출력이 필요하면 순차로 진행한다.
3. 각 위임에는 담당 문서 경로, 소유 파일 범위, 완료 조건을 명시한다.
4. 서브에이전트가 계약 변경을 요청하면 **직접 승인하지 말고** `/contract-sync` 절차를 밟는다.
5. 모두 끝나면 `/demo-check`로 전체 흐름을 확인한다.

## 병렬 위임이 안전한 조합

- `doc-analyzer` + `frontend-integrator` (스키마가 고정되어 있으면 서로 독립)
- `slide-planner` + `presentation-support` + `verifier` (fixture 기준으로 각자 개발)

## 병렬로 하면 안 되는 것

- 같은 파일을 두 에이전트가 동시에 수정 (특히 `contracts.py`, `pipeline.py`)
- 계약이 확정되지 않은 상태에서의 동시 구현 — 반드시 `docs/01`을 먼저 고정한다
