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

export type DurationMinutes = 3 | 5 | 10;

export interface PresentationRequest {
  audience: Audience;
  purpose: Purpose;
  duration_minutes: DurationMinutes;
  keywords: string[];
  style: Style;
  preserve_original_terms: boolean;
  slide_count: number | null;
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

export interface DocumentResponse {
  document: DocumentMeta;
  chunks: Chunk[];
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
