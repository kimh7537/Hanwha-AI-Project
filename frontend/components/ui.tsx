import type { ReactNode } from "react";

import type { ReportStatus, Severity } from "@/lib/types";
import { SEVERITY_LABELS, STATUS_LABELS } from "@/lib/labels";

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-lg border border-line bg-surface ${className}`}>{children}</div>
  );
}

export function SectionTitle({ children, hint }: { children: ReactNode; hint?: string }) {
  return (
    <div className="mb-3">
      <h2 className="text-sm font-semibold tracking-tight">{children}</h2>
      {hint ? <p className="mt-1 text-xs text-muted">{hint}</p> : null}
    </div>
  );
}

/**
 * 상태는 색만으로 구분하지 않는다. 항상 텍스트 라벨을 함께 보여준다
 * (docs/07-frontend-ux.md).
 */
export function StatusBadge({ status }: { status: ReportStatus }) {
  const styles: Record<ReportStatus, string> = {
    ok: "bg-ok-soft text-ok border-ok/30",
    warning: "bg-warn-soft text-warn border-warn/30",
    review_needed: "bg-danger-soft text-danger border-danger/30",
  };
  const marks: Record<ReportStatus, string> = {
    ok: "✓",
    warning: "!",
    review_needed: "✕",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs font-semibold ${styles[status]}`}
    >
      <span aria-hidden>{marks[status]}</span>
      {STATUS_LABELS[status]}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  const styles: Record<Severity, string> = {
    info: "bg-surface-muted text-muted border-line",
    warning: "bg-warn-soft text-warn border-warn/30",
    critical: "bg-danger-soft text-danger border-danger/30",
  };
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded border px-1.5 py-0.5 text-[11px] font-semibold ${styles[severity]}`}
    >
      {SEVERITY_LABELS[severity]}
    </span>
  );
}

/** 고객 청중일 때 결과 상단에 띄우는 배지 (docs/07-frontend-ux.md). */
export function PublicReviewBadge() {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md border border-accent/40 bg-accent-soft px-2.5 py-1 text-xs font-semibold text-accent">
      <span aria-hidden>⚑</span>
      공개 전 검토 필요
    </span>
  );
}

export function ErrorNotice({ message }: { message: string }) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-danger/30 bg-danger-soft px-4 py-3 text-sm text-danger"
    >
      {message}
    </div>
  );
}
