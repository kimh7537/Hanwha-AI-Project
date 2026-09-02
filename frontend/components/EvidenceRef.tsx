"use client";

import type { SourceEvidence } from "@/lib/types";

/** 배지에 적을 말. `chunk-03` 은 내부 식별자라 화면에서는 원문 위치로 바꿔 부른다.
 *
 * 한 슬라이드가 같은 쪽에서 문장을 둘 이상 끌어오면 `3쪽`이 두 개 생겨 어느 쪽을 눌렀는지
 * 알 수 없으므로, 그때만 뒤에 번호를 붙인다. 쪽을 못 찾은 근거는 지우지 않고 식별자로 남긴다.
 */
function labelRefs(refs: string[], evidence: Map<string, SourceEvidence>): string[] {
  const total = new Map<number, number>();
  for (const ref of refs) {
    const page = evidence.get(ref)?.page;
    if (page !== undefined) total.set(page, (total.get(page) ?? 0) + 1);
  }

  const seen = new Map<number, number>();
  return refs.map((ref) => {
    const page = evidence.get(ref)?.page;
    if (page === undefined) return ref;
    if ((total.get(page) ?? 0) < 2) return `${page}쪽`;
    const order = (seen.get(page) ?? 0) + 1;
    seen.set(page, order);
    return `${page}쪽 (${order})`;
  });
}

/**
 * 원문 근거 배지. 클릭하면 그 자리의 원문 문장을 보여준다 (docs/07-frontend-ux.md).
 * 화면에는 `3쪽`처럼 사람이 원문에서 찾아갈 수 있는 위치를 적는다.
 */
export function EvidenceRefs({
  refs,
  evidence,
  onSelect,
}: {
  refs: string[];
  evidence: Map<string, SourceEvidence>;
  onSelect: (id: string) => void;
}) {
  if (refs.length === 0) {
    return (
      <span className="rounded-md border border-danger/30 bg-danger-soft px-2 py-0.5 text-[11px] font-semibold text-danger">
        원문 근거 없음
      </span>
    );
  }

  const labels = labelRefs(refs, evidence);

  return (
    <span className="flex flex-wrap items-center gap-1.5">
      <span className="text-[11px] text-muted">원문 근거</span>
      {refs.map((ref, index) => (
        <button
          key={ref}
          type="button"
          onClick={() => onSelect(ref)}
          title={`클릭하면 원문 ${labels[index]} 문장을 보여줍니다`}
          className="rounded-md border border-line bg-surface-muted/70 px-2 py-0.5 text-[11px] font-semibold text-muted transition-all duration-200 hover:-translate-y-px hover:border-accent/50 hover:bg-accent-soft hover:text-accent"
        >
          {labels[index]}
        </button>
      ))}
    </span>
  );
}

export function EvidenceDialog({
  evidence,
  onClose,
}: {
  evidence: SourceEvidence | null;
  onClose: () => void;
}) {
  if (!evidence) return null;

  return (
    <div
      className="animate-in fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="원문 근거"
      onClick={onClose}
    >
      <div
        className="glass max-h-[80vh] w-full max-w-2xl overflow-auto rounded-2xl border border-line-strong bg-surface p-6"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-bold text-accent">원문 {evidence.page}쪽</p>
            {/* 식별자는 지우지 않고 작게 남긴다 — 개발자가 로그·JSON 과 맞춰 볼 때 쓴다. */}
            <p className="mt-0.5 font-mono text-[11px] text-muted">{evidence.id}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="btn-ghost rounded-lg px-3 py-1.5 text-xs text-muted"
          >
            닫기
          </button>
        </div>
        <p className="whitespace-pre-wrap text-sm leading-[1.85]">{evidence.text}</p>
      </div>
    </div>
  );
}
