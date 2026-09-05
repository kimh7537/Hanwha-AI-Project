// 백엔드 호출. API 키는 절대 여기 두지 않는다 — 모든 LLM 호출은 FastAPI 안에서만 일어난다.

import type {
  AudiencePlansResponse,
  DocumentResponse,
  GenerateResponse,
  PlanPreview,
  PresentationRequest,
  VerificationReport,
} from "./types";

/** 배포된 백엔드. Render 의 상주 프로세스라 인메모리 저장소가 유지된다. */
const DEPLOYED_API = "https://audiencedeck-api.onrender.com";

/**
 * 백엔드 주소. 부를 때마다 정한다.
 *
 * 배포 주소를 코드에 둔 이유: `NEXT_PUBLIC_API_BASE_URL` 은 빌드 시점에 박히는 값이라
 * Vercel 에서 한 번 빠뜨리면 화면은 멀쩡히 뜨고 업로드만 실패한다. 환경변수가 있으면
 * 그것이 이기고, 없으면 로컬(localhost)은 로컬 서버를, 배포 화면은 배포 백엔드를 본다.
 *
 * 상수가 아니라 함수인 것은 서버 렌더링 때문이다. 모듈이 서버에서도 한 번 평가되는데
 * 그때 `window` 가 없어 값이 굳으면 초기 HTML 과 브라우저의 주소가 어긋난다.
 */
function base(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (configured) return configured.replace(/\/$/, "");

  const host = typeof window === "undefined" ? "" : window.location.hostname;
  return host === "localhost" || host === "127.0.0.1" || host === ""
    ? "http://localhost:8000"
    : DEPLOYED_API;
}

/**
 * 잠들어 있는 무료 인스턴스를 미리 깨운다.
 *
 * Render 무료 요금제는 15분 놀면 잠들고 다음 첫 요청이 1분 가까이 걸린다. 그 1분을
 * 업로드 버튼이 맞으면 화면이 멈춘 것으로 보인다. 파일을 고르는 동안 깨워 둔다.
 * 실패해도 화면은 그대로 진행한다.
 */
export function warmUpBackend(): void {
  void fetch(`${base()}/api/health`).catch(() => {});
}

/**
 * `/api/health` 의 답. 파이프라인 데이터가 아니라 "지금 어느 경로로 도는가"라서
 * `contracts.py` 에도 `types.ts` 에도 두지 않는다 (`diff` 와 같은 이유, docs/08).
 */
export type Health = {
  provider: string;
  llm_enabled: boolean;
  render_enabled: boolean;
};

let healthOnce: Promise<Health | null> | null = null;

/**
 * 지금 백엔드가 LLM 을 들고 있는지.
 *
 * 한 번만 묻고 그 약속을 돌려쓴다 — 여러 화면이 같은 것을 물어보는데 Render 무료
 * 인스턴스에 매번 왕복할 이유가 없다. 대신 서버가 도중에 키를 얻어도 새로고침 전까지는
 * 옛 답을 쓴다. 배포는 뜬 뒤로 이 값이 바뀌지 않아 상관없다.
 *
 * 못 닿으면 `null` 이다. "LLM 이 없다"와 "백엔드가 없다"는 다른 사정이고, 후자는
 * 화면이 이미 따로 알린다. 여기서 둘을 뭉치면 서버가 죽었을 때 엉뚱한 안내가 뜬다.
 */
export function fetchHealth(): Promise<Health | null> {
  healthOnce ??= fetch(`${base()}/api/health`)
    .then((response) => (response.ok ? (response.json() as Promise<Health>) : null))
    .catch(() => null);
  return healthOnce;
}

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

const OFFLINE_MESSAGE =
  "백엔드 서버에 연결할 수 없습니다. 서버가 실행 중인지, NEXT_PUBLIC_API_BASE_URL 설정이 맞는지 확인하세요.";

async function send(path: string, init: RequestInit): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`${base()}${path}`, init);
  } catch {
    throw new ApiError(OFFLINE_MESSAGE);
  }

  if (!response.ok) {
    // FastAPI 는 사용자에게 그대로 보여줄 수 있는 한국어 메시지를 detail 로 준다
    let detail = `요청에 실패했습니다. (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") {
        detail = body.detail;
      }
    } catch {
      // JSON 이 아닌 응답이면 기본 메시지를 쓴다
    }
    throw new ApiError(detail);
  }

  return response;
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  return (await send(path, init)).json() as Promise<T>;
}

/**
 * 청중별 설계 규칙. 조건 화면이 생성 전 미리보기에 쓴다.
 *
 * 이것이 없어도 조건 선택과 생성은 그대로 되어야 하므로 실패는 null 로 끝낸다 — 미리보기가
 * 사라질 뿐 데모가 멈추지 않는다.
 */
export async function fetchAudiencePlans(): Promise<AudiencePlansResponse | null> {
  try {
    const response = await fetch(`${base()}/api/audiences`);
    if (!response.ok) return null;
    return (await response.json()) as AudiencePlansResponse;
  } catch {
    return null;
  }
}

/**
 * 지금 조건으로 생성하면 나올 구성. 규칙을 화면에 다시 적지 않으려고 백엔드에 물어본다.
 *
 * 미리보기가 없어도 생성은 그대로 되어야 하므로 실패는 null 로 끝낸다.
 */
export async function fetchPlanPreview(
  presentationRequest: PresentationRequest,
): Promise<PlanPreview | null> {
  try {
    const response = await fetch(`${base()}/api/audiences/preview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(presentationRequest),
    });
    if (!response.ok) return null;
    return (await response.json()) as PlanPreview;
  } catch {
    return null;
  }
}

export async function uploadDocument(file: File): Promise<DocumentResponse> {
  const form = new FormData();
  form.append("file", file);
  return request<DocumentResponse>("/api/documents", { method: "POST", body: form });
}

export async function generatePresentation(
  documentId: string,
  presentationRequest: PresentationRequest,
): Promise<GenerateResponse> {
  return request<GenerateResponse>("/api/presentations/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_id: documentId, request: presentationRequest }),
  });
}

export async function verifyPresentation(presentationId: string): Promise<VerificationReport> {
  return request<VerificationReport>("/api/presentations/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ presentation_id: presentationId }),
  });
}

/** PPTX 는 백엔드(python-pptx)에서 만든다. 파일명도 백엔드가 정한 것을 그대로 쓴다. */
export async function fetchPresentationPptx(
  presentationId: string,
): Promise<{ blob: Blob; filename: string }> {
  const response = await send(`/api/presentations/${presentationId}/export/pptx`, {
    method: "GET",
  });

  return {
    blob: await response.blob(),
    filename:
      filenameFromDisposition(response.headers.get("Content-Disposition")) ??
      `${presentationId}.pptx`,
  };
}

/**
 * 원본 PPTX 슬라이드 한 장의 PNG 주소. `<img src>` 에 그대로 넣는다.
 *
 * 백엔드가 설치된 PowerPoint 로 굽는다. 못 굽는 PC 면 503 이 오고 화면은 글자 비교로 돌아간다.
 */
export function documentSlideUrl(documentId: string, page: number): string {
  return `${base()}/api/documents/${documentId}/slides/${page}`;
}

/** 생성된 발표자료 슬라이드 한 장의 PNG 주소. `number` 는 발표용 덱 기준 1-based. */
export function presentationSlideUrl(presentationId: string, number: number): string {
  return `${base()}/api/presentations/${presentationId}/slides/${number}`;
}

/**
 * 발표용 덱의 각 장이 어느 원본 슬라이드에 얹혔는지.
 *
 * `page` 는 얹은 원본 슬라이드, `output` 은 결과 파일에서 몇 번째 장인가 (둘 다 1-based).
 * 원본에 짝이 없으면 `page` 가, 원본 장수가 모자라 파일에서 빠졌으면 `output` 이 null 이다.
 */
export type SourceMap = {
  source_slides: number;
  cover_page: number | null;
  pairs: { number: number; page: number | null; output: number | null }[];
};

/**
 * 짝짓기를 백엔드에 물어본다. 화면이 규칙을 다시 구현하면 export 가 바뀌는 순간 화면이
 * 실제 파일과 다른 짝을 보여준다 (원본 3장에 얹힌 슬라이드를 표지 옆에 놓는 식).
 *
 * 이것이 없어도 대조 화면은 떠야 하므로 실패는 null 로 끝낸다 — 화면이 글자 기준 짝짓기로 돈다.
 */
export async function fetchSourceMap(presentationId: string): Promise<SourceMap | null> {
  try {
    const response = await fetch(`${base()}/api/presentations/${presentationId}/source-map`);
    if (!response.ok) return null;
    return (await response.json()) as SourceMap;
  } catch {
    return null;
  }
}

/** 슬라이드 위에 얹을 변경 표시 네모. 좌표는 0~1 비율이다. */
export type DiffRegion = { x: number; y: number; w: number; h: number; label: string };

/**
 * 원본 `page` 장과 발표용 `number` 장 사이에서 달라진 자리.
 *
 * 두 렌더가 같은 좌표계라 네모 한 벌이 좌우 양쪽에 함께 맞는다. 표시가 없다고 대조 화면이
 * 멈추면 안 되므로 실패는 빈 목록으로 끝낸다 (PowerPoint 없는 PC 는 503).
 */
export async function fetchSlideDiff(
  presentationId: string,
  number: number,
  page: number,
): Promise<DiffRegion[]> {
  try {
    const response = await fetch(
      `${base()}/api/presentations/${presentationId}/slides/${number}/diff?page=${page}`,
    );
    if (!response.ok) return [];
    return (await response.json()).regions ?? [];
  } catch {
    return [];
  }
}

/** 한국어 파일명은 RFC 5987 (`filename*=UTF-8''...`) 쪽에 들어 있다. */
function filenameFromDisposition(header: string | null): string | null {
  if (!header) return null;

  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(header);
  if (encoded) {
    try {
      return decodeURIComponent(encoded[1]);
    } catch {
      // 잘못 인코딩된 헤더는 무시하고 아래 ASCII 이름을 쓴다
    }
  }

  return /filename="([^"]+)"/i.exec(header)?.[1] ?? null;
}
