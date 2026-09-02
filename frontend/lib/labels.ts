// wire 값(영문) -> 화면 라벨(한국어) 매핑. 이 파일이 유일한 출처다.
// docs/01-contracts.md 의 enum 표와 일치해야 한다.

import type {
  Audience,
  DurationMinutes,
  Interest,
  IssueType,
  Purpose,
  ReportStatus,
  Severity,
  Style,
} from "./types";

export const AUDIENCE_LABELS: Record<Audience, string> = {
  newcomer: "신입사원",
  practitioner: "실무자",
  executive: "임원",
  customer: "고객",
};

export const AUDIENCE_HINTS: Record<Audience, string> = {
  newcomer: "용어를 풀어 설명하고 배경부터 알려줍니다",
  practitioner: "기술 세부사항과 적용 조건을 유지합니다",
  executive: "결론·효과·리스크와 의사결정 포인트를 앞세웁니다",
  customer: "고객 가치 중심으로 바꾸고 내부 정보를 경고합니다",
};

export const INTEREST_LABELS: Record<Interest, string> = {
  technology: "기술",
  performance: "성능",
  cost: "비용",
  safety: "안전성",
  schedule: "일정",
};

/** 이해도 1~5. 색이나 숫자만으로 두지 않고 항상 이 라벨을 함께 보여준다. */
export const EXPERTISE_LABELS: Record<number, string> = {
  1: "입문",
  2: "낮음",
  3: "보통",
  4: "높음",
  5: "전문가",
};

export const PURPOSE_LABELS: Record<Purpose, string> = {
  education: "교육",
  internal_report: "내부보고",
  technical_explanation: "기술설명",
  proposal: "제안",
};

export const STYLE_LABELS: Record<Style, string> = {
  professional: "전문적",
  concise: "간결",
  persuasive: "설득형",
  friendly: "친절한 설명형",
};

export const DURATION_LABELS: Record<DurationMinutes, string> = {
  3: "3분",
  5: "5분",
  10: "10분",
};

export const RECOMMENDED_SLIDES: Record<DurationMinutes, string> = {
  3: "3~4장 권장",
  5: "5장 권장",
  10: "7~8장 권장",
};

export const SEVERITY_LABELS: Record<Severity, string> = {
  info: "정보",
  warning: "주의",
  critical: "심각",
};

// 색만으로 상태를 구분하지 않는다. 항상 이 텍스트 라벨을 함께 표시한다.
export const STATUS_LABELS: Record<ReportStatus, string> = {
  ok: "확인됨",
  warning: "주의",
  review_needed: "검토 필요",
};

export const STATUS_DESCRIPTIONS: Record<ReportStatus, string> = {
  ok: "원문 근거와 어긋나는 내용을 찾지 못했습니다",
  warning: "발표 전에 확인이 필요한 문장이 있습니다",
  review_needed: "원문과 다르거나 근거가 없는 내용이 있습니다",
};

export const ISSUE_TYPE_LABELS: Record<IssueType, string> = {
  unsupported_claim: "원문에 없는 주장",
  number_error: "숫자·단위 오류",
  distortion: "의미 왜곡",
  oversimplification: "과도한 단순화",
  omission: "핵심 내용 누락",
  sensitive_info: "민감·내부 정보",
};

export const PIPELINE_STEPS = [
  "문서 분석",
  "청중 변환",
  "슬라이드 설계",
  "발표 지원",
  "정확성 검증",
] as const;
