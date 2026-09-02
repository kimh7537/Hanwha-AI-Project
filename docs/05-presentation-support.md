# 05. 모듈 D — 발표 지원 AI (`presentation-support`)

**담당 파일:** `backend/app/services/support.py`, `backend/app/prompts/support.py`,
`backend/fixtures/presentation_support.json`, `backend/tests/test_support.py`
**입력:** `SlideDeck` + `AudienceContent` + `PresentationRequest` · **출력:** `PresentationSupport` → `docs/01-contracts.md`

## 슬라이드마다 생성할 것

- **발표 스크립트**: 30~60초 분량(한국어 기준 대략 200~380자). `duration_seconds`에 추정치를 담는다.
- **꼭 말해야 할 한 문장** (`must_say`): 보통 그 슬라이드의 `takeaway`를 발화체로 바꾼 문장.

전체 스크립트 시간 합계가 `duration_minutes`의 ±20% 안에 들어와야 한다.

## 예상 Q&A (3~5개)

**질문은 청중에 따라 달라져야 한다.**

| 청중 | 주로 묻는 것 |
|---|---|
| 신입사원 | 용어 뜻, 왜 필요한지, 내 업무와 무슨 관계인지 |
| 실무자 | 적용 조건, 예외 케이스, 기존 방식과의 차이, 성능 |
| 임원 | 비용, 일정, 리스크, 의사결정 포인트, ROI |
| 고객 | 도입 효과, 우리 환경 적용 가능성, 리스크와 지원 범위 |

- 답변은 `SourceAnalysis`에 있는 사실로만 구성하고 `source_refs`를 붙인다.
- 근거로 답할 수 없는 질문에는 답을 지어내지 말고 "원문 확인 필요"로 표시한다.

## F. AI 관객 리허설 (있으면 좋은 기능)

MVP에서는 실시간 대화가 아니라 **예상 질문 카드 + 보강 추천 슬라이드**면 충분하다.
`rehearsal_cards`: `{question, why, recommended_slide}` — 그 질문이 나올 이유와,
답이 부족한 슬라이드 id를 가리켜 "이 슬라이드를 보강하라"고 알려준다.

## mock / fallback 동작

휴리스틱 경로는 청중별 질문 템플릿에 `terms` / `numbers` / `must_keep` 항목을 채워 넣는다.
템플릿이라도 슬롯 값은 실제 문서에서 와야 하며 `source_refs`가 붙어야 한다.

## 완료 조건

슬라이드 수만큼 스크립트가 생성되고, Q&A가 3~5개이며, 청중을 바꾸면 질문 유형이 실제로 달라진다.
