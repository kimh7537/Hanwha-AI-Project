# 03. 모듈 B — 청중 맞춤 변환 AI (`audience-transformer`) · **핵심 차별화**

**담당 파일:** `backend/app/services/audience.py`, `backend/app/prompts/audience.py`,
`backend/fixtures/audience_content.json`, `backend/tests/test_audience.py`
**입력:** `SourceAnalysis` + `PresentationRequest` · **출력:** `AudienceContent` → `docs/01-contracts.md`

## 절대 규칙

**사실은 유지하고 표현의 깊이만 바꾼다.** 원문에 없는 사실·수치·효과를 청중 맞춤이라는 이유로
추가하지 않는다. 입력은 원문이 아니라 `SourceAnalysis`다.

## 청중별 변환 원칙

| 청중 | 변환 원칙 | 필수 산출 |
|---|---|---|
| 신입사원 `newcomer` | 용어를 풀고, 비유·업무 예시를 넣고, 배경부터 설명 | `glossary` 충실히 채움 |
| 실무자 `practitioner` | 기술 세부사항과 조건을 그대로 유지 | `must_keep` 전부 반영 |
| 임원 `executive` | 결론·효과·리스크·의사결정 포인트 우선 | `emphasis`에 의사결정 포인트 |
| 고객 `customer` | 고객 가치와 적용 효과 중심 | `cautions`에 내부정보/과장 경고 |

## 스타일 축 (청중과 직교)

`professional` 전문적 / `concise` 간결 / `persuasive` 설득형 / `friendly` 친절한 설명형.
스타일은 문장 톤만 바꾸며 정보량을 바꾸지 않는다. `tone_note`에 적용한 톤을 한 줄로 기록한다.

## 원어 유지 (`preserve_original_terms`)

- 켜기: 원문 영문 용어를 그대로 두고 괄호로 한국어 설명을 덧붙인다. (`throughput(처리량)`)
- 끄기: 한국어로 바꾸되 최초 1회는 원어를 병기한다.

## 고객용 경고 (필수)

고객 청중일 때 아래를 발견하면 제거하거나, 제거하지 못하면 `cautions`에 남긴다.
내부 조직명·사내 시스템명·미확인 수치·대외비 표현·과장 표현(`최고`, `100%`, `완벽`, `무조건`).

## mock / fallback 동작

LLM 없이도 동작해야 한다. 휴리스틱 경로는 `SourceAnalysis`의 문장을 **선택·재배열·병합**해
청중별 구성을 만든다(없는 문장을 지어내지 않음). `source_refs`는 원본 항목의 것을 그대로 승계한다.

## 완료 조건

동일한 `SourceAnalysis`로 `newcomer`와 `executive`를 각각 생성했을 때
용어 풀이 개수·설명 깊이·강조점이 **눈에 띄게** 달라지고, 두 결과의 수치 집합은 **동일**해야 한다.
(이 두 조건을 `test_audience.py`에서 검사한다 — 데모 성공 기준 7번의 근거)
