# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 이 저장소를 읽는 법

원본 기획안 `claude-code-implementation-brief.md`는 **전체를 읽지 마라.** 길고, 한 번에 필요한
부분은 일부다. 기획안은 `docs/` 아래 모듈별로 분해되어 있고 각 모듈에는 전용 서브에이전트가 있다.

| 문서 | 내용 | 담당 서브에이전트 |
|---|---|---|
| `docs/00-overview.md` | 프로젝트 정의·파이프라인·평가표 — **공통 전제** | 전원 |
| `docs/01-contracts.md` | 데이터 계약(스키마·enum) — **공통 전제** | 전원 |
| `docs/02-document-analysis.md` | 모듈 A 파싱·chunking·SourceAnalysis | `doc-analyzer` |
| `docs/03-audience-transform.md` | 모듈 B 청중 변환 (차별화 ①) | `audience-transformer` |
| `docs/04-slide-planner.md` | 모듈 C SlideDeck 구성 | `slide-planner` |
| `docs/05-presentation-support.md` | 모듈 D 스크립트·Q&A·리허설 | `presentation-support` |
| `docs/06-verification.md` | 모듈 E 원문 대비 검증 (차별화 ②) | `verifier` |
| `docs/07-frontend-ux.md` | 위저드 UI·결과 탭 | `frontend-integrator` |
| `docs/08-api-and-env.md` | API 초안·환경변수·배포 | `frontend-integrator` |
| `docs/09-schedule-and-demo.md` | 일정·데모 성공 기준 7항목 | — |
| `docs/10-quality-safety.md` | 환각 방지·비밀정보·오류 처리 — **공통 전제** | 전원 |

넓거나 여러 모듈에 걸친 요청을 받으면 **먼저 `/spec-route`로 분해해 위임하라.**

## 프로젝트 정의

`AudienceDeck AI` — 기술문서를 업로드하면 청중/목적/시간/키워드/스타일 조건에 맞춰
**발표자료 + 발표 스크립트 + 예상 Q&A + 원문 대비 검증 리포트**를 생성하는 4일 팀 MVP.

범용 PPT 생성기가 아니다. 차별점은 **청중별 재구성**과 **원문 근거 검증** 두 가지이며,
기능 추가 여부는 이 두 축에 기여하는지로 판단한다.

## 핵심 아키텍처 — 단일 원본, 청중별 변환

```
원문 문서 → SourceAnalysis → AudienceContent → SlideDeck → PresentationSupport → VerificationReport
```

- `SourceAnalysis`가 유일한 사실 원천이다. 이후 단계는 원문이 아니라 `SourceAnalysis`를 입력받는다.
- 청중 변환은 **사실을 유지하고 표현의 깊이만 바꾼다.**
- 모든 수치·주장은 `source_refs`(chunk id)로 원문까지 추적 가능해야 한다.
  근거를 못 찾은 항목은 삭제하지 말고 `unverified`로 넘긴다.
- 각 단계의 출력 스키마가 6인 병렬 개발의 경계다. 계약 변경은 항상 4곳 동시 수정(`/contract-sync`).

## 스킬 (자동 실행 워크플로우)

| 스킬 | 언제 |
|---|---|
| `/spec-route` | 넓은 요청을 모듈로 분해해 서브에이전트에 위임할 때 — **대개 가장 먼저** |
| `/contract-sync` | 계약(Pydantic/TS/fixture/문서) 변경이 필요할 때 |
| `/evidence-audit` | 생성 결과의 원문 근거 무결성을 감사할 때 |
| `/demo-check` | 데모 성공 기준 7항목을 실행으로 검증할 때 |

## 훅 (자동 강제)

`.claude/settings.json`에 등록되어 있으며 스크립트는 `.claude/hooks/`에 있다.
한글 출력을 위해 **UTF-8 BOM으로 저장되어야 한다** — 수정 후에는 인코딩을 확인하라.

| 이벤트 | 훅 | 동작 |
|---|---|---|
| SessionStart | `session-brief.ps1` | 라우팅 맵과 현재 구현 상태를 주입 |
| UserPromptSubmit | `route-hint.ps1` | 요청 키워드로 담당 문서·에이전트를 안내 |
| PreToolUse(Write\|Edit) | `guard-secrets.ps1` | 실제 API 키 기록 및 `.env.example` 값 기입을 **차단** |
| PostToolUse(Write\|Edit) | `contract-guard.ps1` | 계약 한쪽만 수정 시 나머지 3곳을 상기 |
| Stop | `stop-verify.ps1` | 계약 불일치가 남아 있으면 알림 (비차단) |

## 구현 규칙 (위반 시 훅/스킬이 잡는다)

- **mock provider 우선.** API 키·Chroma·배포 계정이 없어도 샘플 문서만으로 전체 데모가 끝까지
  동작해야 한다. LLM 호출 실패 시 휴리스틱으로 fallback하고 `fallback_used: true`를 메타에 남긴다.
- **API 키는 백엔드에만.** 모든 LLM 호출은 FastAPI에서. `.env.example`에는 변수 이름만.
- **원문 전체를 프롬프트에 넣지 않는다.** chunk 단위로 처리한다.
- **근거 없는 점수 금지.** "정확도 92%" 같은 고정 수치 표기 금지.
- **고객 청중**이면 내부정보·과장 표현을 경고하고 "공개 전 검토 필요" 배지를 표시한다.
- UI는 색만으로 상태를 구분하지 않고 텍스트 라벨을 병행한다. 오류·로딩 메시지는 한국어.
- **Day 4에는 새 기능을 만들지 않는다.**

## 환경과 명령

- Python 인터프리터: `backend\.venv\Scripts\python.exe` (**시스템 PATH에 Python 없음**)
- Node 24 / npm 11 사용 가능. **git은 설치되어 있지 않다.**
- 한글 소스 파일을 PowerShell `Get-Content`/`Set-Content`로 다시 쓰지 마라. BOM 없는 UTF-8을
  ANSI로 잘못 읽어 파일이 깨진다. 수정은 Edit/Write 도구로만 한다.

```powershell
# 테스트 (backend 디렉터리에서 실행 — pytest.ini 의 pythonpath 설정 때문)
cd backend; .venv\Scripts\python.exe -m pytest

# 서버
cd backend; .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
cd frontend; npm run dev

# 프론트엔드 타입 검사는 build 로 한다 (LayoutProps 등 Next 생성 타입 때문에 tsc 단독은 실패)
cd frontend; npm run build

# 스킬 스크립트 (저장소 루트에서)
backend\.venv\Scripts\python.exe .claude\skills\demo-check\run_demo.py
backend\.venv\Scripts\python.exe .claude\skills\contract-sync\check_contracts.py
backend\.venv\Scripts\python.exe backend\scripts\build_fixtures.py   # 계약 변경 후 fixture 재생성
backend\.venv\Scripts\python.exe backend\scripts\build_sample_pptx.py  # PPTX 입력 fixture 재생성
```

## 구현 현황

모듈 A~E, 파이프라인, API, 위저드 UI, 테스트 101개까지 구현되어 있고 `/demo-check` 7항목이 전부
통과한다. 입력은 PDF / PPTX / TXT 를 지원하고, 출력은 PPTX / Markdown / JSON 다운로드를 지원한다.
미구현(선택): Chroma 임베딩 검색, DOCX 입력, 결과 영구 저장.

### 코드에서 이미 내린 판단 (되돌리기 전에 이유를 확인할 것)

- **휴리스틱 경로는 문장을 지어내지 않고 원문 문장을 고르고 재배열한다.** mock 이 캔드 JSON을
  반환하면 검증 모듈이 의미를 잃는다.
- **슬라이드 bullet 은 문장을 40자로 자르지 않는다.** 규칙만으로는 의미 압축이 불가능해
  자르면 "줄었" 같은 깨진 어미가 남는다. 명세의 "40자 내외"는 LLM 경로 기준이다.
- **LLM 응답은 Pydantic 검증만으로 믿지 않는다.** 계약의 모든 필드에 기본값이 있어 형태가 다른
  JSON도 '빈 결과'로 통과한다. 각 단계에 실질성 검사가 있다 (`_is_substantive` 등).
- **검증의 숫자 대조는 단위까지 포함한 토큰으로만 한다.** 값만 비교하면 "3만 건"의 3이
  "3개 부서"의 3과 겹쳐 오탐이 난다.
- **PPTX export 는 새 문장을 만들지 않는다.** 검증을 마친 `GenerateResponse` 를 배치만 한다.
  파일 안에서 문장을 요약하거나 자르면 `source_refs` 대응이 깨진다. 넘치면 글자를 줄인다.
- **화면 라벨의 원본은 `frontend/lib/types.ts` 옆의 `labels.ts` 다.** PPTX 가 백엔드에서
  만들어져 `app/services/labels.py` 에 미러가 있고, `tests/test_labels_mirror.py` 가 대조한다.
