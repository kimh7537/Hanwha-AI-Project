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
- 청중 변환은 **사실을 유지한 채 표현·정보 선택·구성을 모두 바꾼다.** 문장만 쉬워지고 덱의 뼈대가
  그대로면 "프롬프트 옵션을 UI로 만든 것"과 구분되지 않는다. 청중이 바뀌면 **무엇을 넣고 뺄지,
  몇 장으로 나눌지, 어떤 순서로 둘지**가 함께 바뀌어야 한다. 사실 자체를 바꾸는 것은 금지다.
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
backend\.venv\Scripts\python.exe backend\scripts\check_chroma.py     # Chroma Cloud 연결·순위 점검
```

## 구현 현황

모듈 A~E, 파이프라인, API, 위저드 UI, 테스트 169개까지 구현되어 있고 `/demo-check` 7항목이 전부
통과한다. 입력은 PDF / PPTX / TXT 를 지원하고, 출력은 PPTX / Markdown / JSON 다운로드를 지원한다.
청중 프로파일(이해도·관심 영역·사전지식)과 메시지 통제(반드시 전달·강조·최소화·사용 금지)를
조건 화면에서 받는다. Chroma Cloud 임베딩 검색은 `CHROMA_*` 가 모두 설정된 경우에만 켜지고
실패 시 keyword 로 되돌아간다.
미구현(선택): DOCX 입력, 결과 영구 저장.

### 코드에서 이미 내린 판단 (되돌리기 전에 이유를 확인할 것)

- **청중별 이야기 순서의 유일한 출처는 `audience.AUDIENCE_STORYLINE` 이다.** 이 값이 세 곳으로
  간다 — 휴리스틱 경로의 `explanations` 순서, LLM 프롬프트의 구성 지시, 조건 화면의 생성 전
  미리보기(`/api/audiences`). 어디 한 곳에 문자열을 다시 적으면 화면이 실제로 일어나지 않는
  구성을 예고하게 된다. `tests/test_audience_storyline.py` 가 선언과 결과를 대조한다.
- **화면은 생성 전에 뼈대를 예고하고, 결과 화면이 같은 모양으로 되짚는다.** 조건 화면의 "이야기
  순서"와 결과의 "실제로 만들어진 순서"가 짝이다. 심사자가 가장 먼저 의심하는 것이 "프롬프트
  옵션을 UI 로 만든 것 아닌가"라서, 청중을 바꾸는 순간 뼈대가 바뀌는 것을 누르기 전에 보여준다.
- **미리보기는 규칙을 화면에 옮겨 적지 않고 `POST /api/audiences/preview` 로 물어본다.** 이해도가
  용어 풀이 개수를 움직이고 메시지 통제가 순위를 바꾸면서 규칙이 늘어난 뒤로는, 화면이 그
  계산을 따라 하면 실제 결과와 어긋난다. 생성 경로와 같은 함수를 부른다.
- **`profile`(청중 프로파일)과 `message`(메시지 통제)는 사실을 만들지도 지우지도 않는다.**
  `services/profile.py` 가 하는 일은 점수를 매겨 순서를 바꾸는 것뿐이다. `minimize` 는 삭제가
  아니라 감점이고, `banned` 는 고르는 단계에서 피하되 남으면 검증이 잡는다. 여기서 문장을
  지우기 시작하면 원문 대비 검증이라는 나머지 절반이 무너진다.
- **`must_convey` 를 덱에 넣어 주지 않는다.** 근거 없는 문장을 슬라이드에 심는 일이라서다.
  뒷받침할 원문 사실을 앞으로 당기고, 덱에서 확인되지 않으면 검증이 `omission` 으로 알린다.
- **이해도(`expertise`)는 청중을 덮어쓰지 않고 한 단계 더 좁힌다.** 임원 기본은 용어 풀이 0개지만
  이해도가 낮으면 늘어난다. 기술을 모르는 임원에게 용어 풀이를 주지 않는 것은 청중 규칙을 지킨
  것이 아니라 발표를 실패시키는 것이다. 이해도 3 이 "청중 기본값 그대로"라 기본 요청은 안 바뀐다.
- **화면의 "강조"는 `message` 가 아니라 `keywords` 에 담긴다.** 그 필드가 이미 "덱에 최소 1회
  등장하고 검증에서 확인한다"는 뜻으로 분석·검색·검증에 물려 있어, 이름만 옮기면 그 배선이
  전부 끊긴다. 화면에서만 한 묶음으로 보여준다.
- **슬라이드 장수는 시간이 상한을, 청중이 밀도를 정한다.** 신입 +1 / 실무자 +1 / 임원 −1
  (`planner.AUDIENCE_SLIDE_DELTA`). 시간만 보면 청중을 바꿔도 덱의 뼈대가 그대로라
  차별화가 화면에 드러나지 않는다. 사용자가 `slide_count` 를 직접 주면 보정을 걸지 않는다.
- **화면의 기본값은 원본 장수다.** 업로드가 PPTX 이고 원본이 3~10장이면 `slide_count` 를
  원본 장수로 채워 둔다(`page.tsx sourceSlideCount`). 원본이 몇 장인지 모르는 채로 장수를
  고르라는 화면은 답할 수가 없다. 다만 그동안은 위 청중 보정이 걸리지 않으므로,
  `시간·청중에 맞춰` 를 골랐을 때 몇 장이 되는지를 항상 같은 화면에 함께 적는다.
- **`SlideDeck.strategy` 는 비워 두지 않는다.** "왜 이 순서·이 분량인가"가 화면의 근거라서,
  LLM 이 안 채우면 `build_strategy()` 의 규칙 문장으로 덮는다. 설계 의도만 적는 칸이므로
  원문 사실이 아니고 `source_refs` 도 검증 대상도 아니다.
- **청중 비교는 전용 엔드포인트를 만들지 않는다.** `generate` 를 audience 만 바꿔 한 번 더 부르고
  결과를 컴포넌트 안에만 둔다. 비교는 보고 나면 끝나는 화면이라 저장할 이유가 없다.
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
- **원본 위에 얹을 때 갈아 끼우지 않은 텍스트 상자는 비운다.** 원본에 텍스트 상자가 여럿이면
  (좌우 2단, 하단 주석) 가장 큰 하나만 바뀌고 나머지에 원문이 그대로 남아, 검증을 마친 결과
  옆에 검증하지 않은 문장이 섞였다. 도형은 지우지 않고 글만 비운다. 그룹 안의 글은 도해·로고인
  경우가 많아 건드리지 않는다 — 그림을 지키는 쪽을 택했다.
- **제목 placeholder 가 없으면 맨 위 텍스트 상자를 제목 자리로 본다.** 빈 레이아웃 위에 직접
  만든 자료가 흔한데, `shapes.title` 이 None 이면 생성된 제목이 어디에도 안 들어가고 원본 제목이
  그대로 남는다. 상자가 하나뿐이거나 맨 위가 곧 가장 큰 상자면 본문 자리를 뺏으므로 쓰지 않는다.
- **글자 크기는 도형의 폭·높이로 정한다.** 글자 수만 보면 5.8인치 상자와 12인치 상자에 같은
  크기를 내줘 좁은 쪽이 그대로 넘친다. 문장은 자르지 않으므로 줄일 수 있는 것은 크기뿐이다.
- **입력이 PPTX 면 export 는 원본 파일 위에 얹는다.** 빈 프레젠테이션에 새로 그리면 사용자가
  만들어 둔 이미지·표·배경·글꼴이 전부 사라진다. 원본 바이트를 `StoredDocument.source` 에
  들고 있다가 `build_pptx(result, template=...)` 로 넘기고, 원본 슬라이드에서는 텍스트
  프레임의 글만 바꾼다. 발표 시간에 맞춘 덱이라 짝이 없는 원본 슬라이드는 빠진다.
- **화면 라벨의 원본은 `frontend/lib/types.ts` 옆의 `labels.ts` 다.** PPTX 가 백엔드에서
  만들어져 `app/services/labels.py` 에 미러가 있고, `tests/test_labels_mirror.py` 가 대조한다.
- **검색은 프롬프트 예산을 넘길 때만 돈다.** 문서가 `max_prompt_chars` 안에 들어가면 chunk 전부가
  프롬프트에 들어가므로 순위가 무의미하다. 작은 문서에서 Chroma 를 호출하면 데모에 불필요한
  네트워크 의존만 생긴다. mock 경로에서는 검색을 아예 건너뛴다.
- **Chroma 실패는 `fallback_used` 를 켜지 않는다.** 그 플래그는 "LLM 응답 실패"를 뜻하고 화면에
  배지로 뜬다. 검색 경로 강등은 `RunContext.notes` 에만 남긴다.
- **Chroma 클라이언트는 자격증명별로 캐시한다.** `CloudClient` 생성자가 tenant/database 확인으로
  네트워크를 타므로, `/api/health` 와 매 생성 요청이 각각 새로 만들면 그 왕복이 그대로 쌓인다.
- **Chroma query 는 `include=[]` 로 id 만 받는다.** 기본값은 documents·metadatas·distances 까지
  돌려주는데 우리는 id 만 쓰고, Chroma Cloud 는 반환 데이터에 요금을 매긴다.
- **컬렉션 개수가 chunk 수와 같으면 재색인하지 않는다.** 같은 문서로 청중만 바꿔 다시 생성하는
  것이 데모의 기본 동선이라, 임베딩 계산과 쓰기 요금을 다시 치를 이유가 없다.
- **테스트는 `conftest.py` 에서 provider 와 `CHROMA_*` 를 강제로 비운다.** 실 `.env` 가 있는
  개발기에서 테스트가 실제 API 를 호출하면 느리고 비용이 들며, LLM 출력이 매번 달라
  휴리스틱을 단정한 테스트가 깨진다.
