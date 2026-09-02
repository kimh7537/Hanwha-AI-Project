// 백엔드 호출. API 키는 절대 여기 두지 않는다 — 모든 LLM 호출은 FastAPI 안에서만 일어난다.

import type {
  AudiencePlansResponse,
  DocumentResponse,
  GenerateResponse,
  PlanPreview,
  PresentationRequest,
  VerificationReport,
} from "./types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

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
    response = await fetch(`${BASE_URL}${path}`, init);
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
    const response = await fetch(`${BASE_URL}/api/audiences`);
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
    const response = await fetch(`${BASE_URL}/api/audiences/preview`, {
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
  return `${BASE_URL}/api/documents/${documentId}/slides/${page}`;
}

/** 생성된 발표자료 슬라이드 한 장의 PNG 주소. `number` 는 발표용 덱 기준 1-based. */
export function presentationSlideUrl(presentationId: string, number: number): string {
  return `${BASE_URL}/api/presentations/${presentationId}/slides/${number}`;
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
      `${BASE_URL}/api/presentations/${presentationId}/slides/${number}/diff?page=${page}`,
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
