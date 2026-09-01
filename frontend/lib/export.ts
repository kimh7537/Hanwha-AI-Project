// 결과를 파일로 내려받는다. PPTX export 가 없어도 데모가 성립해야 한다
// (docs/04-slide-planner.md).

import type { GenerateResponse } from "./types";
import { AUDIENCE_LABELS, ISSUE_TYPE_LABELS, SEVERITY_LABELS, STATUS_LABELS } from "./labels";

export function toMarkdown(result: GenerateResponse): string {
  const { slide_deck, presentation_support, verification_report, request } = result;
  const scriptOf = (slideId: string) =>
    presentation_support.scripts.find((script) => script.slide_id === slideId);

  const lines: string[] = [
    `# ${slide_deck.title}`,
    "",
    `- 청중: ${AUDIENCE_LABELS[request.audience]}`,
    `- 발표 시간: ${request.duration_minutes}분`,
    `- 필수 키워드: ${request.keywords.join(", ") || "없음"}`,
    "",
    "---",
    "",
  ];

  slide_deck.slides.forEach((slide, index) => {
    const script = scriptOf(slide.id);
    lines.push(`## ${index + 1}. ${slide.title}`, "");
    lines.push(`**핵심 한 줄** ${slide.takeaway}`, "");
    slide.bullets.forEach((bullet) => lines.push(`- ${bullet}`));
    lines.push("", `추천 시각자료: ${slide.visual_suggestion}`);
    lines.push(`원문 근거: ${slide.source_refs.join(", ") || "없음"}`, "");
    if (script) {
      lines.push(`### 발표 스크립트 (약 ${script.duration_seconds}초)`, "", script.script, "");
      lines.push(`> 꼭 말할 것: ${script.must_say}`, "");
    }
  });

  lines.push("---", "", "## 예상 질문과 답변", "");
  presentation_support.qa.forEach((item) => {
    lines.push(`**Q. ${item.question}**`, "", `A. ${item.answer}`, "");
    lines.push(`원문 근거: ${item.source_refs.join(", ") || "없음"}`, "");
  });

  if (verification_report) {
    lines.push("---", "", "## 원문 대비 검증", "");
    lines.push(`상태: ${STATUS_LABELS[verification_report.status]}`, "");
    lines.push(verification_report.summary, "");
    verification_report.items.forEach((item) => {
      lines.push(
        `- [${SEVERITY_LABELS[item.severity]}] ${ISSUE_TYPE_LABELS[item.type]}` +
          `${item.slide_id ? ` (${item.slide_id})` : ""}: ${item.message}`,
      );
      lines.push(`  - 수정 제안: ${item.suggested_fix}`);
    });
    lines.push("");
  }

  lines.push(
    "---",
    "",
    "이 자료는 업로드한 원문을 근거로 생성되었습니다. 발표 전 담당자 검토가 필요합니다.",
    "",
  );

  return lines.join("\n");
}

export function download(filename: string, content: string, mime: string): void {
  downloadBlob(filename, new Blob([content], { type: `${mime};charset=utf-8` }));
}

/** PPTX 처럼 백엔드가 만들어 준 바이너리를 그대로 내려받는다. */
export function downloadBlob(filename: string, blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
