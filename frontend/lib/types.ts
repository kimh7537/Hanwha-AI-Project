// 공통 데이터 계약 (TypeScript 미러)
// backend/app/models/contracts.py 와 의미상 동일해야 한다.
// 필드를 바꾸면 4곳(Pydantic / TypeScript / fixtures / docs)을 함께 고친다. -> contract-sync 스킬

export type Audience = "newcomer" | "practitioner" | "executive" | "customer";
export type Purpose =
  | "education"
  | "internal_report"
  | "technical_explanation"
  | "proposal";
export type Style = "professional" | "concise" | "persuasive" | "friendly";
export type Severity = "info" | "warning" | "critical";
export type ReportStatus = "ok" | "warning" | "review_needed";
export type IssueType =
  | "unsupported_claim"
  | "number_error"
  | "distortion"
  | "oversimplification"
  | "omission"
  | "sensitive_info";

export type Interest = "technology" | "performance" | "cost" | "safety" | "schedule";

export type DurationMinutes = 3 | 5 | 10;

/** `Audience` 가 '누구'라면 이쪽은 '어느 정도로, 무엇에 관심 있는 사람'이다.
 *
 * 사실을 바꾸지 않고, 어떤 사실을 앞으로 당기고 얼마나 풀어 쓸지를 정한다.
 */
export interface AudienceProfile {
  /** 기술 이해도 1(낮음) ~ 5(높음) */
  expertise: number;
  interests: Interest[];
  /** 이미 알고 있는 것 */
  prior_knowledge: string;
}

/** 발표자가 발표의 의도를 직접 통제한다.
 *
 * 화면의 "강조"는 이 객체가 아니라 `PresentationRequest.keywords` 에 담긴다 — 그 필드가 이미
 * "덱에 최소 1회 등장하고 검증한다"는 뜻으로 백엔드에 물려 있다. 화면에서는 한 묶음으로 본다.
 */
export interface MessageControl {
  /** 이 발표로 반드시 남겨야 할 한 문장 */
  must_convey: string;
  /** 덜 다루고 싶은 주제. 삭제가 아니라 뒤로 민다. */
  minimize: string[];
  /** 쓰지 말아야 할 표현 */
  banned: string[];
}

export interface PresentationRequest {
  audience: Audience;
  purpose: Purpose;
  duration_minutes: DurationMinutes;
  /** 강조 키워드. 덱에 최소 1회 등장해야 하고 검증에서 확인한다. */
  keywords: string[];
  style: Style;
  preserve_original_terms: boolean;
  slide_count: number | null;
  profile: AudienceProfile;
  message: MessageControl;
}

/** 청중 하나의 설계 규칙. `/api/audiences` 응답 — 공통 계약이 아니라 이 화면 전용이다.
 *
 * 조건 화면이 생성 전에 "이 청중이면 이 순서로 짜입니다"를 예고하는 데 쓴다. 값을 프론트에
 * 적어 두지 않고 받아 오는 이유는, 규칙을 고칠 때 조용히 갈라지면 화면이 실제로 일어나지 않는
 * 일을 예고하게 되기 때문이다. 원본은 backend `services/audience.AUDIENCE_STORYLINE`.
 */
export interface AudiencePlan {
  audience: Audience;
  label: string;
  /** 이 청중일 때 만들어지는 설명의 순서. 덱의 뼈대다. */
  storyline: string[];
  /** 무엇을 앞세우는가 */
  leads: string;
  /** 무엇을 덜어내는가 */
  trims: string;
  /** 용어 풀이 최대 개수. null 은 전부. */
  glossary_limit: number | null;
  /** 같은 시간이라도 이 청중이면 장수가 몇 장 움직이는가 */
  slide_delta: number;
}

/** 이번 조건으로 지금 생성하면 나올 구성. `POST /api/audiences/preview` 응답.
 *
 * 이해도가 용어 풀이 개수를 움직이고 메시지 통제가 순위를 바꾸는 규칙이 늘어난 뒤로는, 화면이
 * 그 계산을 따라 하면 실제 결과와 어긋나기 쉽다. 생성 경로와 같은 함수를 부른 값을 받는다.
 */
export interface PlanPreview {
  audience: Audience;
  label: string;
  storyline: string[];
  leads: string;
  trims: string;
  /** 이해도까지 반영한 최종 용어 풀이 개수. null 은 전부. */
  glossary_limit: number | null;
  slide_count: number;
  /** 프로파일·메시지 통제가 이번 구성에 무엇을 했는지 */
  notes: string[];
}

export interface AudiencePlansResponse {
  audiences: AudiencePlan[];
  /** 발표 시간(분) -> 기본 장수. JSON 이라 키가 문자열이다. */
  duration_slides: Record<string, number>;
  min_slides: number;
  max_slides: number;
}

export interface Chunk {
  id: string;
  index: number;
  page: number;
  text: string;
}

export interface DocumentMeta {
  document_id: string;
  filename: string;
  page_count: number;
  char_count: number;
  chunk_count: number;
}

/** 원본 한 쪽(PPTX 는 슬라이드 한 장)의 글. chunk 는 쪽 경계를 넘으므로 따로 받는다. */
export interface PageContent {
  page: number;
  text: string;
}

export interface DocumentResponse {
  document: DocumentMeta;
  chunks: Chunk[];
  pages: PageContent[];
}

export interface SourceEvidence {
  id: string;
  text: string;
  page: number;
}

export interface EvidenceItem {
  text: string;
  source_refs: string[];
}

export interface NumberFact {
  value: string;
  unit: string;
  meaning: string;
  source_refs: string[];
}

export interface TermFact {
  term: string;
  definition: string;
  source_refs: string[];
}

export interface SourceAnalysis {
  core_message: string;
  technical_points: EvidenceItem[];
  key_features: EvidenceItem[];
  numbers: NumberFact[];
  terms: TermFact[];
  must_keep: EvidenceItem[];
  source_evidence: SourceEvidence[];
  unverified: string[];
}

export interface AudienceExplanation {
  topic: string;
  text: string;
  source_refs: string[];
}

export interface GlossaryItem {
  term: string;
  plain_definition: string;
  source_refs: string[];
}

export interface AudienceContent {
  audience: Audience;
  tone_note: string;
  explanations: AudienceExplanation[];
  glossary: GlossaryItem[];
  emphasis: string[];
  cautions: string[];
}

export interface Slide {
  id: string;
  title: string;
  takeaway: string;
  bullets: string[];
  visual_suggestion: string;
  speaker_notes: string;
  source_refs: string[];
}

export interface SlideDeck {
  title: string;
  /** 이 청중이라서 왜 이 순서·이 분량인지. 청중이 바뀌면 함께 바뀐다. */
  strategy: string;
  slides: Slide[];
}

export interface SlideScript {
  slide_id: string;
  script: string;
  must_say: string;
  duration_seconds: number;
}

export interface QAItem {
  question: string;
  answer: string;
  source_refs: string[];
  asked_by: Audience;
}

export interface RehearsalCard {
  question: string;
  why: string;
  recommended_slide: string;
}

export interface PresentationSupport {
  scripts: SlideScript[];
  qa: QAItem[];
  rehearsal_cards: RehearsalCard[];
}

export interface VerificationItem {
  severity: Severity;
  slide_id: string;
  type: IssueType;
  message: string;
  source_refs: string[];
  suggested_fix: string;
}

export interface VerificationReport {
  summary: string;
  status: ReportStatus;
  items: VerificationItem[];
  checked_slides: number;
}

export interface PipelineMeta {
  provider: string;
  fallback_used: boolean;
  fallback_reason: string;
  elapsed_ms: number;
}

export interface GenerateRequest {
  document_id: string;
  request: PresentationRequest;
}

export interface GenerateResponse {
  presentation_id: string;
  document: DocumentMeta;
  request: PresentationRequest;
  source_analysis: SourceAnalysis;
  audience_content: AudienceContent;
  slide_deck: SlideDeck;
  presentation_support: PresentationSupport;
  verification_report: VerificationReport | null;
  meta: PipelineMeta;
}

export interface VerifyRequest {
  presentation_id?: string;
  document_id?: string;
  request?: PresentationRequest;
  slide_deck?: SlideDeck;
  presentation_support?: PresentationSupport;
}
