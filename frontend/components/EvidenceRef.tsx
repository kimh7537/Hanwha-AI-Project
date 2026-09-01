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
      <span className="rounded border border-danger/30 bg-danger-soft px-1.5 py-0.5 text-[11px] font-medium text-danger">
        원문 근거 없음
      </span>
    );
  }

  return (
    <span className="flex flex-wrap items-center gap-1">
      <span className="text-[11px] text-muted">원문 근거</span>
      {refs.map((ref) => (
        <button
          key={ref}
          type="button"
          onClick={() => onSelect(ref)}
          title="클릭하면 원문 문장을 보여줍니다"
          className="rounded border border-line bg-surface-muted px-1.5 py-0.5 font-mono text-[11px] text-muted transition-colors hover:border-accent/50 hover:bg-accent-soft hover:text-accent"
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
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="원문 근거"
      onClick={onClose}
    >
      <div
        className="max-h-[80vh] w-full max-w-2xl overflow-auto rounded-lg border border-line bg-surface p-5 shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between gap-4">
          <div>
            <p className="font-mono text-xs text-accent">{evidence.id}</p>
            <p className="text-xs text-muted">페이지 {evidence.page}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-line px-2 py-1 text-xs text-muted hover:bg-surface-muted"
          >
            닫기
          </button>
        </div>
        <p className="whitespace-pre-wrap text-sm leading-relaxed">{evidence.text}</p>
      </div>
    </div>
  );
}
