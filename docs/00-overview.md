# 00. 프로젝트 개요 (모든 에이전트 필독)

> 원본 기획안: `claude-code-implementation-brief.md` (분해 전 전체본, 참조용)

## 한 문장 정의

기술문서를 입력하면 청중 / 발표 목적 / 발표 시간 / 필수 키워드 / 표현 스타일에 맞춰 발표자료와
발표 스크립트·예상 Q&A를 생성하고, 생성 결과가 원문 근거를 벗어나지 않았는지 검증하는 AI 발표 지원 솔루션.

서비스명(임시): **AudienceDeck AI**

> 핵심 메시지: 자료를 만드는 AI가 아니라, 청중이 이해할 때까지 리허설하는 AI.

## 이 프로젝트가 아닌 것

범용 PPT 생성기가 **아니다**. 차별점은 두 가지뿐이며, 기능 추가 여부는 이 두 축에 기여하는지로 판단한다.

1. **청중별 재구성** — 같은 사실을 신입/실무자/임원/고객에게 다른 깊이로 설명
2. **원문 근거 검증** — 생성 결과가 원문을 벗어났는지 기계적으로 검사

## 파이프라인 (아키텍처의 전부)

```
원문 문서
  → SourceAnalysis        (모듈 A · docs/02)
  → AudienceContent       (모듈 B · docs/03)
  → SlideDeck             (모듈 C · docs/04)
  → PresentationSupport   (모듈 D · docs/05)
  → VerificationReport    (모듈 E · docs/06)
```

**단일 원본 원칙:** 청중별 결과물을 원문에서 각각 생성하지 않는다. `SourceAnalysis`가 유일한 사실
원천이며, 이후 모든 단계는 원문이 아니라 `SourceAnalysis`를 입력으로 받는다. 청중 변환은
**사실을 유지하고 표현의 깊이만 바꾼다.**

각 단계의 출력 JSON 스키마가 팀 6인의 병렬 개발 경계다 → `docs/01-contracts.md`

## MVP 입력값

| 항목 | 값 |
|---|---|
| 기술문서 | PDF, PPTX, TXT (DOCX는 시간이 남을 때) |
| 청중 | 신입사원 \| 실무자 \| 임원 \| 고객 |
| 발표 목적 | 교육 \| 내부보고 \| 기술설명 \| 제안 |
| 발표 시간 | 3분 \| 5분 \| 10분 |
| 필수 키워드 | 쉼표 구분 자유 입력 |
| 표현 스타일 | 전문적 \| 간결 \| 설득형 \| 친절한 설명형 |
| 원어 유지 | 켜기 \| 끄기 |
| 슬라이드 수 | 발표 시간 기준 자동 추천 |

## MVP 출력값

1. 슬라이드 미리보기 (제목 / takeaway / bullet / 원문 근거)
2. 슬라이드별 발표 스크립트
3. 예상 질문 3~5개 + 권장 답변
4. 원문 대비 검증 리포트
5. (여유 시) PPTX 다운로드 — 없으면 HTML preview + JSON/Markdown 다운로드 우선

## 이번 MVP 제외 범위

로그인·권한·결제 / 사내 메일·드라이브·메신저 연동 / 동시 편집 / 완전한 디자인 편집기 /
외부 PPT 서비스 연동(자격증명이 이미 있을 때만) / 근거 없는 "정확도 92%" 식 고정 점수

## 기술 스택

- Frontend: Next.js (App Router) + TypeScript + Tailwind
- Backend: FastAPI + Pydantic
- 문서 추출: PyMuPDF(PDF), python-pptx(PPTX), plain text parser
- LLM: 환경변수로 고르는 provider adapter (Claude / OpenAI / **mock**)
- Retrieval: chunk + keyword/embedding. Chroma Cloud는 설정된 경우에만, 없으면 메모리/JSON fallback
- 슬라이드: React HTML preview 우선, 여유 시 `python-pptx`
- 테스트: pytest(backend) + 최소 smoke test(frontend)

## 6인 역할 = 6개 서브에이전트

| 역할 | 서브에이전트 | 담당 문서 |
|---|---|---|
| 문서 분석 | `doc-analyzer` | docs/02 |
| 청중 변환 | `audience-transformer` | docs/03 |
| 발표 구조 | `slide-planner` | docs/04 |
| 발표 지원 | `presentation-support` | docs/05 |
| 검증 | `verifier` | docs/06 |
| 통합/UI/PM | `frontend-integrator` | docs/07, docs/08 |

## 평가 기준 (100점)

| 항목 | 배점 | 구현/발표에서 보여줄 근거 |
|---|---:|---|
| 적합한 AI 툴 선택 및 활용 | 25 | 분석·변환·검증에 LLM, 근거·숫자 검사에 규칙 로직을 병용하고 각 단계 입출력을 설명 |
| 가공된 산출물의 퀄리티 | 25 | 청중별로 실제 깊이·표현이 달라지는 자료, 출처가 붙은 결과 |
| 논리적 원인 분석 | 15 | 기존 준비 병목(자료 읽기→구조→PPT→스크립트→Q&A)을 Before 화면·시간 측정으로 제시 |
| 데이터 근거 해결책 도출 | 15 | 동일 문서 기준 소요시간·수정 횟수·오류 건수 비교 (최소 3회 테스트 중앙값) |
| 실질적 기대효과 | 10 | 신입 교육·팀 보고·고객 제안 시나리오와 절감 준비시간 |
| 현실적 구현 가능성 | 10 | MVP 범위 / 사람 검토 단계 / mock fallback / 향후 연동 계획을 분리해 설명 |

예시값과 실제 측정값은 반드시 구분해 표기한다.
