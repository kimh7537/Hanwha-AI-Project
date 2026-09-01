# 04. 모듈 C — Presentation Planner AI (`slide-planner`)

**담당 파일:** `backend/app/services/planner.py`, `backend/app/prompts/planner.py`,
`backend/app/services/export_pptx.py`(선택), `backend/fixtures/slide_deck.json`, `backend/tests/test_planner.py`
**입력:** `AudienceContent` + `SourceAnalysis` + `PresentationRequest` · **출력:** `SlideDeck` → `docs/01-contracts.md`

## 권장 기본 구성

1. 발표 목적 / 문제 배경
2. 기술 또는 해결 방식
3. 작동 원리 / 핵심 내용
4. 주요 장점 또는 가치
5. 결론 및 다음 행동

## 시간에 따른 분량 원칙

| 발표 시간 | 슬라이드 수 | 구성 원칙 |
|---|---|---|
| 3분 | 3~4장 | 결론 우선 |
| 5분 | 5장 | 핵심 원리와 효과 포함 |
| 10분 | 7~8장 | 배경·사례·리스크 추가 |

`request.slide_count`가 주어지면 그 값을 우선하되 3~10장으로 클램프한다.

## 슬라이드 규칙

- `takeaway`는 **한 문장**이며 그 슬라이드에서 청중이 가져갈 결론이다.
- `bullets`는 3~5개, 각 40자 내외. 문단을 그대로 붙여넣지 않는다.
- **모든 슬라이드는 `source_refs`를 1개 이상 갖는다.** (데모 성공 기준 4번)
- `visual_suggestion`은 "무엇을 그릴지"를 한 줄로. 이미지 생성은 하지 않는다.
- `speaker_notes`는 모듈 D가 스크립트로 확장할 씨앗 문장 수준으로 짧게 둔다.
- 필수 키워드(`request.keywords`)는 최소 1회 이상 덱 안에 등장해야 한다.

## 렌더링

React 기반 HTML preview가 1순위. `python-pptx` PPTX export는 **다른 모든 것이 끝난 뒤에만** 손댄다.
export가 미구현이어도 JSON / Markdown 다운로드로 데모가 성립해야 한다.

### PPTX export (`app/services/export_pptx.py`, 구현됨)

`GET /api/presentations/{id}/export/pptx` — 저장된 `GenerateResponse` 를 그대로 배치한다.

- **export 는 새 문장을 만들지 않는다.** 요약·재작성을 하면 검증을 마친 문장과 파일 내용이
  달라져 `source_refs` 대응이 깨진다. 넘칠 때는 문장을 자르지 말고 글자 크기를 줄인다.
- 구성: 표지 → 본문 슬라이드 → 부록(예상 Q&A) → 부록(원문 대비 검증).
- 본문 슬라이드 하단에 `추천 시각자료` 와 `원문 근거: chunk-…` 를 항상 인쇄한다.
- 발표자 노트에는 모듈 D 의 스크립트·꼭 말할 것·근거가 들어간다.
- 고객 청중이면 표지에 `공개 전 검토 필요` 를 **글자로** 남긴다(색만으로 구분하지 않는다).
- 한글 글꼴은 `a:latin` 만으로는 적용되지 않는다. `a:ea`(동아시아) 도 함께 지정한다.
- 화면 라벨은 `frontend/lib/labels.ts` 가 원본이고 `app/services/labels.py` 가 미러다.
  둘이 어긋나면 `tests/test_labels_mirror.py` 가 잡는다.

## mock / fallback 동작

휴리스틱 경로는 `AudienceContent.explanations`와 `SourceAnalysis`의 항목을 위 5단 구성 슬롯에
분배해 덱을 만든다. 각 슬라이드의 `source_refs`는 사용한 항목의 refs를 합집합으로 승계한다.

## 완료 조건

5분·고객 조건으로 5장 안팎이 생성되고, 모든 슬라이드에 유효한 `source_refs`가 있으며,
`request.keywords`가 덱 안에 등장한다.
