"use client";

import type { SourceEvidence } from "@/lib/types";

/**
 * 원문 근거 배지. 클릭하면 해당 chunk 의 원문 문장과 페이지를 보여준다
 * (docs/07-frontend-ux.md).
 */
export function EvidenceRefs({
  refs,
  onSelect,
}: {
  refs: string[];
  onSelect: (id: string) => void;
}) {
  if (refs.length === 0) {
    return (
      <span className="rounded-md border border-danger/30 bg-danger-soft px-2 py-0.5 text-[11px] font-semibold text-danger">
        원문 근거 없음
      </span>
    );
  }

  return (
    <span className="flex flex-wrap items-center gap-1.5">
      <span className="text-[11px] text-muted">원문 근거</span>
      {refs.map((ref) => (
        <button
          key={ref}
          type="button"
          onClick={() => onSelect(ref)}
          title="클릭하면 원문 문장을 보여줍니다"
          className="rounded-md border border-line bg-surface-muted/70 px-2 py-0.5 font-mono text-[11px] text-muted transition-all duration-200 hover:-translate-y-px hover:border-accent/50 hover:bg-accent-soft hover:text-accent"
        >
          {ref}
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
            <p className="font-mono text-xs font-semibold text-accent">{evidence.id}</p>
            <p className="mt-0.5 text-[11px] text-muted">페이지 {evidence.page}</p>
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
