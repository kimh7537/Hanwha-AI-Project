# 08. API · 환경변수 · 배포

## API 초안

```text
POST /api/documents
  multipart/form-data (file) → { document, chunks, pages }
  파일 업로드 및 chunk 생성

POST /api/presentations/generate
  { document_id, request: PresentationRequest }
  → { presentation_id, document, request, source_analysis, audience_content,
      slide_deck, presentation_support, verification_report, meta }

POST /api/presentations/verify
  { presentation_id }  또는  { document_id, slide_deck, presentation_support, request }
  → VerificationReport

GET  /api/presentations/{id}          (선택) 저장된 결과 조회

GET  /api/presentations/{id}/export/pptx
  → application/vnd.openxmlformats-officedocument.presentationml.presentation
  저장된 결과를 PPTX 로 내려준다. 새로 생성하지 않으므로 LLM 호출이 없다.
```

export 는 다운로드이므로 `GET` 이다. 파일명이 한국어라 `Content-Disposition` 에 ASCII 대체
이름과 RFC 5987 이름(`filename*=UTF-8''…`)을 함께 담고, CORS `expose_headers` 로 노출한다.
python-pptx 가 없는 환경에서는 **503 + 한국어 안내**로 끝내고 앱은 계속 동작한다.

`generate` 는 검증까지 마친 결과를 한 번에 돌려준다. `verify` 는 자료를 수정한 뒤 다시 검사할 때
쓰며, 화면의 5단계 진행 표시는 generate(1~4단계)와 verify(5단계) 호출에 대응한다.

`GET /api/health` 는 provider 모드(`mock` / `anthropic` / `openai`)를 함께 반환해
데모 중 어떤 경로로 동작 중인지 화면에서 확인할 수 있게 한다.

## 환경변수

**API 키는 프론트엔드에 노출하지 않는다.** 모든 LLM 호출은 FastAPI에서만 수행하고,
`.env.example`에는 **변수 이름만** 넣는다(실제 값 금지 — PreToolUse 훅이 차단한다).

```text
LLM_PROVIDER=            # mock | anthropic | openai  (기본 mock)
LLM_API_KEY=
LLM_MODEL=
CHROMA_API_KEY=
CHROMA_TENANT=
CHROMA_DATABASE=
NEXT_PUBLIC_API_BASE_URL=
```

## provider adapter 규칙

- `LLM_PROVIDER` 하나로 mock / anthropic / openai를 전환한다.
- 키가 없거나 호출이 실패하면 **자동으로 휴리스틱(mock) 경로로 fallback**하고,
  응답 메타에 `fallback_used: true`와 사유를 담아 화면에서 설명할 수 있게 한다.
- 키·자격증명이 없다는 이유로 핵심 기능이 멈추면 안 된다.

## 배포 구조

```text
Browser
  → Next.js frontend (Vercel)
  → FastAPI backend (Render 또는 Railway)
       → LLM API
       → Chroma Cloud (선택)
       → 파일 저장소 또는 개발용 로컬 저장
```

배포 환경변수나 Chroma Cloud가 없어도 **샘플 문서 + mock provider로 로컬에서 즉시 시연**되어야 한다.

## 로컬 실행

```powershell
# backend
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000   # cwd: backend
# frontend
npm run dev                                                                     # cwd: frontend
```
