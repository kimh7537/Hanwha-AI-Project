# 01. 공통 데이터 계약 (모든 에이전트 필독 · 변경 시 전원 합의)

Python Pydantic 모델과 TypeScript 타입은 **의미상 동일**해야 한다.
계약을 바꾸면 다음 4곳을 항상 함께 고친다 → `/contract-sync` 스킬이 이 절차를 강제한다.

1. `backend/app/models/contracts.py` (Pydantic)
2. `frontend/lib/types.ts` (TypeScript)
3. `backend/fixtures/*.json` (샘플 fixture)
4. 해당 모듈 문서(docs/02~06)의 스키마 예시

## enum 값 (wire 값은 영문 snake_case, 화면 라벨은 한국어)

| enum | wire 값 | 라벨 |
|---|---|---|
| `audience` | `newcomer` / `practitioner` / `executive` / `customer` | 신입사원 / 실무자 / 임원 / 고객 |
| `purpose` | `education` / `internal_report` / `technical_explanation` / `proposal` | 교육 / 내부보고 / 기술설명 / 제안 |
| `style` | `professional` / `concise` / `persuasive` / `friendly` | 전문적 / 간결 / 설득형 / 친절한 설명형 |
| `duration_minutes` | `3` / `5` / `10` | — |
| `severity` | `info` / `warning` / `critical` | 정보 / 주의 / 심각 |
| `report_status` | `ok` / `warning` / `review_needed` | 확인됨 / 주의 / 검토 필요 |
| `issue_type` | `unsupported_claim` / `number_error` / `distortion` / `oversimplification` / `omission` / `sensitive_info` | — |

## PresentationRequest

```json
{
  "audience": "customer",
  "purpose": "technical_explanation",
  "duration_minutes": 5,
  "keywords": ["정확도", "도입 효과"],
  "style": "persuasive",
  "preserve_original_terms": true,
  "slide_count": 5
}
```

`slide_count`가 null이면 `duration_minutes`로 자동 추천(3분→3~4, 5분→5, 10분→7~8).

## Document / Chunk

```json
{
  "document": {
    "document_id": "doc-a1b2c3",
    "filename": "sample.pdf",
    "page_count": 4,
    "char_count": 8123,
    "chunk_count": 12
  },
  "chunks": [
    {"id": "chunk-01", "index": 0, "page": 1, "text": "..."}
  ]
}
```

`chunk id`는 `chunk-01` 형식(1-based, 2자리 zero-pad). 모든 `source_refs`는 이 id를 가리킨다.

## SourceAnalysis (모듈 A 출력)

```json
{
  "core_message": "",
  "technical_points": [{"text": "", "source_refs": ["chunk-03"]}],
  "key_features":    [{"text": "", "source_refs": ["chunk-02"]}],
  "numbers": [{"value": "", "unit": "", "meaning": "", "source_refs": ["chunk-03"]}],
  "terms":   [{"term": "", "definition": "", "source_refs": ["chunk-02"]}],
  "must_keep": [{"text": "", "source_refs": ["chunk-05"]}],
  "source_evidence": [{"id": "chunk-01", "text": "", "page": 1}],
  "unverified": ["근거를 찾지 못한 항목 설명"]
}
```

## AudienceContent (모듈 B 출력)

```json
{
  "audience": "customer",
  "tone_note": "고객 가치 중심, 내부 용어 제거",
  "explanations": [{"topic": "", "text": "", "source_refs": ["chunk-02"]}],
  "glossary":     [{"term": "", "plain_definition": "", "source_refs": ["chunk-02"]}],
  "emphasis":     ["이 청중에게 강조할 포인트"],
  "cautions":     ["내부정보 가능성 등 경고"]
}
```

## SlideDeck (모듈 C 출력)

```json
{
  "title": "",
  "strategy": "",
  "slides": [{
    "id": "slide-1",
    "title": "",
    "takeaway": "",
    "bullets": [],
    "visual_suggestion": "",
    "speaker_notes": "",
    "source_refs": ["chunk-01"]
  }]
}
```

`strategy`는 **왜 이 순서·이 분량으로 구성했는지**다. 청중이 바뀌면 이 문장도 바뀐다.
원문 사실을 적는 칸이 아니라 설계 의도를 적는 칸이므로 `source_refs`를 갖지 않는다.

## PresentationSupport (모듈 D 출력)

```json
{
  "scripts": [{"slide_id": "slide-1", "script": "", "must_say": "", "duration_seconds": 45}],
  "qa": [{"question": "", "answer": "", "source_refs": ["chunk-04"], "asked_by": "customer"}],
  "rehearsal_cards": [{"question": "", "why": "", "recommended_slide": "slide-3"}]
}
```

## VerificationReport (모듈 E 출력)

```json
{
  "summary": "근거 확인이 필요한 문장 1건",
  "status": "warning",
  "items": [{
    "severity": "warning",
    "slide_id": "slide-3",
    "type": "oversimplification",
    "message": "조건 X가 생략되어 표현이 과도하게 단순화되었습니다.",
    "source_refs": ["chunk-04"],
    "suggested_fix": "조건 X를 bullet에 추가하세요."
  }]
}
```

`status` 결정 규칙: `critical` 1건 이상 → `review_needed` / `warning` 1건 이상 → `warning` / 그 외 → `ok`.

## 불변 규칙

- 모든 사실 항목은 `source_refs`를 가진다. 근거가 없으면 **삭제하지 말고** `unverified`로 넘긴다.
- `source_refs`에 들어가는 id는 반드시 해당 문서의 `source_evidence`에 존재해야 한다 (검증 대상).
- 필드를 삭제·개명하지 말고 추가만 한다. 삭제가 필요하면 팀 합의 후 4곳 동시 수정.
