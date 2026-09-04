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

GET  /api/documents/{id}/slides/{page}        원본 PPTX 슬라이드 1장
GET  /api/presentations/{id}/slides/{number}  결과 PPTX 슬라이드 1장
  → image/png
  원본과 결과를 눈으로 대조하는 화면(docs/07)이 쓴다.

GET  /api/presentations/{id}/slides/{number}/diff?page={원본 쪽}
  → { regions: [{ x, y, w, h, label }] }
  위 두 PNG 를 픽셀로 대조해 달라진 자리를 돌려준다. 좌표는 0~1 비율이고
  두 렌더의 좌표계가 같아 네모 한 벌이 좌우 양쪽에 함께 맞는다.

GET  /api/presentations/{id}/source-map
  → { source_slides, cover_page, pairs: [{ number, page, output }] }
  발표용 덱 `number` 장이 어느 원본 슬라이드(`page`)에 얹혀 결과 파일 몇 장째(`output`)로
  들어갔는지. 셋 다 1-based 이고, 짝이 없으면 `page`, 파일에서 빠졌으면 `output` 이 null.
```

`source-map` 이 있는 이유: 짝짓기 규칙(표지 제외, 근거 최빈 원본 우선, 못 찾으면 남은 원본을
앞에서부터)은 `export_pptx` 만 알고 있다. 대조 화면이 같은 규칙을 옮겨 적으면 한쪽만 자랄 때
화면이 실제 파일과 다른 짝을 보여준다. `slides/{number}` 도 이 배치로 파일 쪽수를 찾는다 —
"덱 N 장 = 파일 N+1 장" 이 아니다.

`diff` 는 파이프라인 데이터가 아니라 화면 표시 보조라서 `contracts.py` 에 두지 않는다
(계약 4곳 동기화 대상이 아니다). 렌더링은 두 번 다 캐시를 탄다 — 화면이 두 이미지를 이미
띄운 뒤에 부르기 때문이다. Pillow 가 없거나 대조에 실패하면 `regions` 는 빈 목록이다.

export 는 다운로드이므로 `GET` 이다. 파일명이 한국어라 `Content-Disposition` 에 ASCII 대체
이름과 RFC 5987 이름(`filename*=UTF-8''…`)을 함께 담고, CORS `expose_headers` 로 노출한다.
python-pptx 가 없는 환경에서는 **503 + 한국어 안내**로 끝내고 앱은 계속 동작한다.

`generate` 는 검증까지 마친 결과를 한 번에 돌려준다. `verify` 는 자료를 수정한 뒤 다시 검사할 때
쓰며, 화면의 5단계 진행 표시는 generate(1~4단계)와 verify(5단계) 호출에 대응한다.

`GET /api/health` 는 provider 모드(`mock` / `anthropic` / `openai`)를 함께 반환해
데모 중 어떤 경로로 동작 중인지 화면에서 확인할 수 있게 한다.

슬라이드 PNG 는 윈도우에서는 설치된 PowerPoint 를 COM 으로, 리눅스(배포)에서는 LibreOffice 로
PDF 를 거쳐 굽는다(`services/render_slides.py`). 못 굽는 환경이면 **503 + 한국어 안내**로
끝내고 화면은 글자 비교로 되돌아간다 — `/api/health` 의 `render_enabled` 가 이 가능 여부를
알려준다. 렌더링은 데모의 전제가 아니다.

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
ALLOWED_ORIGINS=         # 배포한 프론트엔드 주소. 쉼표로 여러 개. localhost 는 항상 허용
```

`ALLOWED_ORIGINS` 는 배포에서만 의미가 있다. 화면과 API 가 다른 도메인에 놓이는 순간
브라우저가 Origin 을 글자 그대로 대조하므로, 여기에 배포 주소가 없으면 화면에는
"백엔드 서버에 연결할 수 없습니다"만 뜨고 서버 로그에는 아무 흔적도 남지 않는다.

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

실제 배포 설정은 저장소 루트의 `render.yaml`(백엔드 설계도)에 있다. 절차는 `README.md` 의
"배포" 절을 따른다. 백엔드는 **상주 프로세스여야 한다** — 업로드한 문서와 생성 결과가
`services/store.py` 의 인메모리 저장소에 있어서, 서버리스로 올리면 업로드와 생성이
서로 다른 인스턴스에 떨어져 "문서를 찾을 수 없습니다"가 난다.

## 로컬 실행

```powershell
# backend
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000   # cwd: backend
# frontend
npm run dev                                                                     # cwd: frontend
```
