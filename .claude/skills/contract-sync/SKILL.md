---
name: contract-sync
description: 공통 데이터 계약(SourceAnalysis, AudienceContent, SlideDeck, PresentationSupport, VerificationReport, PresentationRequest)을 변경할 때 Pydantic·TypeScript·fixture·문서 4곳을 동기화한다. contracts.py 또는 lib/types.ts를 수정했거나, 필드 추가/개명/삭제가 필요하거나, "타입이 안 맞는다"는 문제가 생겼을 때 사용한다.
---

# 계약 동기화

이 프로젝트에서 데이터 계약은 **6인이 병렬 개발하기 위한 유일한 경계**다.
한쪽만 고치면 마지막 통합에서 반드시 깨진다.

## 원칙

- 필드는 **추가만** 한다. 삭제·개명은 팀 합의 후에만.
- wire 값은 영문 snake_case(`customer`), 화면 라벨은 한국어(`고객`).
  라벨 매핑은 `frontend/lib/labels.ts` **한 곳에만** 둔다.
- 모든 사실 항목은 `source_refs`를 갖는다. 이 규칙을 깨는 변경은 거부하라.

## 절차 (순서대로)

1. **원본 확인** — `docs/01-contracts.md`를 읽는다. 이 문서가 계약의 기준이다.
2. **문서 먼저 수정** — `docs/01-contracts.md`의 JSON 예시와 enum 표를 먼저 고친다.
3. **Pydantic** — `backend/app/models/contracts.py`를 문서에 맞춘다.
   기본값을 넣어 기존 fixture가 깨지지 않게 한다(`Field(default_factory=list)` 등).
4. **TypeScript** — `frontend/lib/types.ts`를 미러링한다. Optional 여부까지 일치시킨다.
5. **fixture** — `backend/fixtures/*.json` 전부를 새 스키마로 갱신한다.
6. **모듈 문서** — 영향받는 `docs/02`~`docs/06`의 스키마 예시를 고친다.
7. **검증** — 아래 스크립트를 실행한다.

```powershell
backend\.venv\Scripts\python.exe .claude\skills\contract-sync\check_contracts.py
```

8. **테스트** — `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`

## 보고

무엇을 왜 바꿨는지, 그리고 **어느 모듈 담당자가 코드를 고쳐야 하는지**를 명시하라.
(예: "`AudienceContent.cautions` 추가 → `audience-transformer`와 `frontend-integrator`가 반영 필요")
