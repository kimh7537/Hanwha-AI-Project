# 02. 모듈 A — 문서 분석 AI (`doc-analyzer`)

**담당 파일:** `backend/app/services/document_parser.py`, `chunking.py`, `retrieval.py`, `analyzer.py`,
`backend/app/prompts/analysis.py`, `backend/fixtures/source_analysis.json`, `backend/tests/test_chunking.py`, `test_analyzer.py`
**출력 계약:** `SourceAnalysis` → `docs/01-contracts.md`

## 책임

원문에서 **아래 항목만** 추출한다. 문서에 없는 사실은 절대 추가하지 않는다.

1. 핵심 메시지 (`core_message`)
2. 핵심 기술 및 주요 특징 (`technical_points`, `key_features`)
3. 수치와 단위 (`numbers`)
4. 전문용어와 쉬운 정의 (`terms`)
5. 반드시 유지해야 하는 조건/주의사항 (`must_keep`)
6. 위 모든 항목의 원문 근거 (`source_refs` = chunk id, `source_evidence`에 페이지·짧은 인용)

## 불변 규칙

- 문서에 없는 사실을 추가하지 않는다.
- 숫자는 **원문에 존재하는 값만** 사용한다. 반올림·환산·추정 금지.
- 근거를 찾지 못한 내용은 삭제하지 말고 `unverified` 배열에 사유와 함께 남긴다.
- 원문 전체를 한 프롬프트에 넣지 않는다. chunk 단위로 처리한 뒤 병합한다.

## 파싱 / 청킹 규칙

- PDF는 PyMuPDF로 페이지별 텍스트 추출, TXT는 UTF-8(실패 시 cp949) 디코딩.
- PPTX는 python-pptx로 **슬라이드 1장 = 페이지 1개**로 추출한다. 제목을 맨 앞에 두고 나머지
  도형은 배치 순서(위→아래, 왼→오른쪽)로 읽는다. z-order 는 화면 배치와 무관하기 때문이다.
  표는 행 단위(`셀 | 셀`)로 펴고, 그룹 도형은 안쪽까지 내려가며, 발표자 노트도 원문의 일부로
  `[발표자 노트]` 표시와 함께 읽는다. 구버전 `.ppt` 는 지원하지 않고 변환을 안내한다.
- chunk 크기 목표 800~1200자, 문단 경계 우선, 100자 내외 overlap.
- 각 chunk는 `{id, index, page, text}`를 갖고, id는 `chunk-01` 형식 1-based zero-pad 2자리.
- 페이지 정보를 잃지 않는다. 근거 클릭 시 "페이지 N"을 보여줘야 하기 때문.
- 빈 문서·텍스트 추출 실패·미지원 확장자는 사용자 친화적 한국어 오류로 반환한다(빈 결과 금지).

## Retrieval

MVP는 작은 문서 대상이므로 keyword 기반으로 충분하다.
`CHROMA_API_KEY`가 설정된 경우에만 Chroma Cloud를 쓰고, 없으면 메모리/JSON fallback으로 동작한다.
Chroma 연결 실패가 파이프라인을 중단시켜서는 안 된다.

## mock / fallback 동작

`LLM_PROVIDER=mock`이거나 LLM 호출이 실패하면 **규칙 기반 휴리스틱 분석**으로 대체한다.
캔드(canned) JSON을 반환하지 말 것 — 실제 업로드 문서에서 뽑아야 검증 모듈이 의미를 갖는다.

- `numbers`: 정규식으로 숫자+단위/% 추출, 해당 문장을 `meaning`, chunk id를 `source_refs`
- `terms`: `X란 ~이다`, `X: 정의`, 괄호 병기, 대문자 약어(`[A-Z]{2,}`) 패턴
- `must_keep`: `반드시 / 주의 / 필수 / 제한 / 조건 / 이상 / 미만` 포함 문장
- `key_features`: 불릿(`- • 1.`)으로 시작하는 줄
- `core_message`: 필수 키워드 적중이 가장 높은 문장

## 완료 조건 (Day 1)

`backend/fixtures/sample_document.txt`를 입력하면 유효한 `SourceAnalysis` JSON이 나오고,
모든 `numbers` / `terms` 항목이 실제 존재하는 chunk id를 가리킨다. `pytest backend/tests/test_analyzer.py` 통과.
