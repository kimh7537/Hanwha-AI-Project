# AudienceDeck AI

기술문서를 업로드하면 **청중 / 발표 목적 / 발표 시간 / 필수 키워드 / 표현 스타일**에 맞춰
발표자료와 발표 스크립트·예상 Q&A를 만들고, 생성 결과가 **원문 근거를 벗어나지 않았는지 검증**하는
AI 발표 지원 도구.

> 자료를 만드는 AI가 아니라, 청중이 이해할 때까지 리허설하는 AI.

## 이 도구의 차별점

1. **청중별 재구성** — 같은 사실을 신입사원·실무자·임원·고객에게 다른 깊이로 설명한다.
   사실은 유지하고 표현의 깊이만 바꾼다.
2. **원문 근거 검증** — 모든 슬라이드에 원문 chunk 근거가 붙고, 생성 결과를 원문과 기계적으로 대조해
   근거 없는 주장·숫자 오류·의미 왜곡·조건 누락·고객용 민감정보를 잡아낸다.

이 도구는 발표 준비를 **가속**할 뿐 사람 검토를 대체하지 않는다. 검증 리포트는 "확인이 필요한 지점"을
알려주는 것이며, 최종 책임은 발표자에게 있다.

> 기능과 내부 동작 방식은 **[FEATURES.md](FEATURES.md)** 에 정리되어 있다.
> 이 README는 실행 방법과 배포를 다룬다.

---

## 빠른 시작 (API 키 없이 동작)

`LLM_PROVIDER` 기본값은 `mock`이다. **API 키가 없어도 전체 데모가 끝까지 돌아간다.**
mock 모드는 정해진 답을 재생하는 것이 아니라, 업로드한 실제 문서에서 규칙 기반으로 사실을 추출한다.

### 1. 백엔드

```powershell
# 최초 1회: 가상환경 + 의존성
python -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

# 실행 (http://localhost:8000)
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

`GET http://localhost:8000/api/health` 로 현재 provider(`mock` / `anthropic` / `openai`)를 확인할 수 있다.

### 2. 프론트엔드

```powershell
cd frontend
npm install
npm run dev      # http://localhost:3000
```

`frontend/.env.local` 에 백엔드 주소를 넣는다.

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### 3. 데모 시나리오

1. `backend/fixtures/sample_document.txt` 를 업로드한다.
2. `고객 / 기술설명 / 5분 / 설득형` 을 고르고 키워드에 `정확도, 도입 효과` 를 넣는다.
3. 5장 안팎의 발표자료, 슬라이드별 스크립트, 예상 Q&A, 검증 리포트가 나온다.
4. 근거 배지(`chunk-03`)를 클릭하면 원문 문장과 페이지가 뜬다.
5. 같은 문서로 청중만 `신입사원` 으로 바꾸면 용어 풀이와 설명 깊이가 달라진다.

---

## 환경변수

실제 값은 `.env`(gitignore 대상)에만 둔다. `.env.example` 에는 변수 이름만 있다.
`.env` 는 저장소 루트 또는 `backend/` 어느 쪽에 두어도 읽는다.

| 변수 | 설명 |
|---|---|
| `LLM_PROVIDER` | `mock`(기본) / `anthropic` / `openai` |
| `LLM_API_KEY` | provider API 키. 없으면 자동으로 mock 으로 동작한다 |
| `LLM_MODEL` | 생략 시 provider 기본 모델 (Anthropic: `claude-opus-5`) |
| `CHROMA_API_KEY` / `CHROMA_TENANT` / `CHROMA_DATABASE` | 선택. 없으면 메모리 fallback |
| `NEXT_PUBLIC_API_BASE_URL` | 프론트엔드가 바라볼 백엔드 주소 |

**API 키는 프론트엔드에 두지 않는다.** 모든 LLM 호출은 FastAPI 안에서만 일어난다.

LLM 호출이 실패하면 규칙 기반 경로로 자동 대체되고, 응답 `meta.fallback_used` 와 화면 상단
안내로 그 사실이 드러난다. 데모가 중간에 멈추지 않는다.

---

## 아키텍처 — 단일 원본, 청중별 변환

```
원문 문서
  → SourceAnalysis        (사실·수치·용어·근거)
  → AudienceContent       (청중별 설명)
  → SlideDeck             (발표 구조)
  → PresentationSupport   (스크립트·Q&A·리허설 카드)
  → VerificationReport    (원문 대비 검증)
```

청중별 결과물을 원문에서 각각 만들지 않는다. `SourceAnalysis` 가 유일한 사실 원천이고,
이후 모든 단계는 원문이 아니라 앞 단계의 출력을 입력으로 받는다. 그래서 청중을 바꿔도
**수치와 사실은 그대로**이고 설명의 깊이만 달라진다.

**AI 도구 분담:** 문서 분석과 자연어 재구성은 LLM이, 원문 근거 대조·숫자 검사·조건 누락 판정은
결정론적 규칙 로직이 담당한다. 그래서 검증 결과는 같은 입력에 항상 같다.

### 디렉터리

```
backend/app/
  models/contracts.py     공통 데이터 계약 (Pydantic)
  services/analyzer.py    모듈 A 문서 분석
  services/audience.py    모듈 B 청중 변환
  services/planner.py     모듈 C 슬라이드 구성
  services/support.py     모듈 D 스크립트·Q&A
  services/verifier.py    모듈 E 원문 대비 검증
  services/pipeline.py    A→E 오케스트레이션
  services/export_pptx.py PPTX 파일 생성
  llm/                    provider adapter (mock / anthropic / openai)
frontend/
  lib/types.ts            계약의 TypeScript 미러
  components/             업로드 → 조건 → 생성 → 결과 탭
docs/                     모듈별 명세 (기획안 분해본)
.claude/                  서브에이전트 · 스킬 · 훅
```

---

## API

```text
GET  /api/health                        provider 모드 확인
POST /api/documents                     업로드 및 chunk 생성
POST /api/presentations/generate        SourceAnalysis ~ VerificationReport 생성
POST /api/presentations/verify          저장된 결과 재검증
GET  /api/presentations/{id}            저장된 결과 조회
GET  /api/presentations/{id}/export/pptx  PPTX 다운로드
```

`generate` 는 검증 리포트까지 함께 돌려준다. `verify` 는 자료를 수정한 뒤 다시 검사할 때 쓴다.

---

## 테스트

```powershell
cd backend
.venv\Scripts\python.exe -m pytest          # 101개
```

`backend/.env` 의 `LLM_PROVIDER` 가 `mock` 이외로 설정되어 있으면 provider 단언 2건이 실패한다.
테스트는 `LLM_PROVIDER=mock` 으로 돌린다.

프론트엔드 타입 검사와 빌드:

```powershell
cd frontend
npm run build
```

데모 성공 기준 7항목을 실행으로 확인하는 스크립트:

```powershell
backend\.venv\Scripts\python.exe .claude\skills\demo-check\run_demo.py
backend\.venv\Scripts\python.exe .claude\skills\evidence-audit\audit.py .claude\skills\demo-check\out\customer.json
```

계약(Pydantic ↔ TypeScript) 동기화 검사:

```powershell
backend\.venv\Scripts\python.exe .claude\skills\contract-sync\check_contracts.py
```

fixture 재생성 (계약을 바꾼 뒤):

```powershell
backend\.venv\Scripts\python.exe backend\scripts\build_fixtures.py
```

---

## 배포

```text
Browser
  → Next.js frontend (Vercel)
  → FastAPI backend (Render 또는 Railway)
       → LLM API
       → Chroma Cloud (선택)
```

- 프론트엔드: Vercel에 `frontend/` 를 연결하고 환경변수 `NEXT_PUBLIC_API_BASE_URL` 에 배포된 백엔드 주소를 넣는다.
- 백엔드: `pip install -r backend/requirements.txt` 후
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (작업 디렉터리 `backend/`).
  환경변수로 `LLM_PROVIDER`, `LLM_API_KEY` 를 넣는다.
- `backend/app/main.py` 의 CORS `allow_origins` 에 배포된 프론트엔드 도메인을 추가해야 한다.
- 현재 저장 방식은 인메모리다. 서버를 재시작하면 업로드한 문서와 생성 결과가 사라진다.

---

## 현재 구현 범위와 남은 것

**구현됨** — 업로드·파싱(PDF/PPTX/TXT)·청킹, 모듈 A~E 전체, mock/실 LLM provider 전환과 자동 fallback,
위저드 UI 4단계, 결과 4개 탭, 근거 클릭 조회, 고객용 경고, PPTX/Markdown/JSON 다운로드,
백엔드 테스트 101개.

**미구현(선택 기능)** — Chroma Cloud 임베딩 검색(현재는 keyword/메모리 fallback),
DOCX 입력, 결과 영구 저장, 실시간 AI 관객 대화(현재는 예상 질문 카드).
