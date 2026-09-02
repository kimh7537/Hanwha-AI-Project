# 06. 모듈 E — 검증 AI (`verifier`) · **핵심 차별화**

**담당 파일:** `backend/app/services/verifier.py`, `backend/app/prompts/verify.py`,
`backend/fixtures/verification_report.json`, `backend/tests/test_verifier.py`
**입력:** `SlideDeck` + `PresentationSupport` + `SourceAnalysis` + 원문 chunk
**출력:** `VerificationReport` → `docs/01-contracts.md`

## 검사 항목 5가지

| # | `type` | 검사 내용 |
|---|---|---|
| 1 | `unsupported_claim` | 원문에 없는 주장 / `source_refs`가 비었거나 존재하지 않는 chunk id를 가리킴 |
| 2 | `number_error` | 슬라이드·스크립트의 숫자·단위가 원문 chunk에 없거나 다름 |
| 3 | `distortion` | 의미 왜곡 (원문의 조건부 서술이 단정으로 바뀜) |
| 4 | `oversimplification` | `must_keep` 조건이 덱 어디에도 반영되지 않음 |
| 5 | `omission` | 핵심 내용 누락 / `request.keywords` 미등장 |
| + | `sensitive_info` | 고객용 자료의 내부·민감 정보 위험 |

## 규칙 로직 우선 (평가표 근거)

문서 분석·재구성은 LLM, **근거·숫자 검사는 규칙 로직**을 쓴다. 이 분담 자체가 평가 항목
"적합한 AI 툴 선택"의 증거다. 아래는 LLM 없이 결정론적으로 판정 가능하므로 규칙으로 구현한다.

- `source_refs` 존재성: 모든 ref가 `source_analysis.source_evidence`의 id 집합에 있는가
- 숫자 대조: 덱/스크립트에서 정규식으로 뽑은 숫자 토큰이 원문 chunk 텍스트에 존재하는가
- `must_keep` 반영 여부: 각 항목의 핵심 토큰이 덱 텍스트에 등장하는가
- 키워드 누락: `request.keywords` 각각이 덱에 등장하는가
- 민감/과장 표현 사전 매칭: `내부`, `사내`, `대외비`, `기밀`, `최고`, `100%`, `완벽`, `무조건`

LLM 패스는 3번(의미 왜곡)처럼 규칙으로 잡기 어려운 항목에만 추가로 쓰고, 실패해도 규칙 결과만으로
리포트가 완성되어야 한다.

## 상태 판정

`critical` ≥1 → `review_needed`(검토 필요) / `warning` ≥1 → `warning`(주의) / 그 외 → `ok`(확인됨)

`summary`는 한국어 한 문장으로 무엇을 왜 확인해야 하는지 쓴다.
각 항목에는 반드시 `suggested_fix`(사용자가 바로 실행 가능한 수정 지시)를 넣는다.

## 금지 사항

**근거 없는 신뢰도 점수를 만들지 않는다.** "정확도 92%" 같은 고정 수치 표기 금지.
점수를 표시하려면 산식이 코드에 명시적으로 구현되어 있고 화면에서 설명 가능해야 한다.

## 완료 조건

데모 문서 기준으로 최소 1건의 "주의" 또는 "확인됨" 결과가 **설명 가능하게** 나온다.
일부러 숫자를 틀린 fixture를 넣으면 `number_error`가 잡히는 테스트가 있다.
