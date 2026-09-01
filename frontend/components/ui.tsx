import type { ButtonHTMLAttributes, ReactNode } from "react";

import type { ReportStatus, Severity } from "@/lib/types";
import { SEVERITY_LABELS, STATUS_LABELS } from "@/lib/labels";

export function Card({
  children,
  className = "",
  hover = false,
  delay,
}: {
  children: ReactNode;
  className?: string;
  /** 목록 카드처럼 여러 장이 늘어설 때만 켠다. 단독 카드가 들썩이면 산만하다. */
  hover?: boolean;
  /** 진입 애니메이션 지연(초). 목록에서 순차 등장시킬 때 쓴다. */
  delay?: number;
}) {
  return (
    <div
      style={delay === undefined ? undefined : { animationDelay: `${delay}s` }}
      className={`glass animate-in rounded-2xl border border-line ${hover ? "lift" : ""} ${className}`}
    >
      {children}
    </div>
  );
}

export function Button({
  variant = "ghost",
  className = "",
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" }) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold disabled:cursor-not-allowed";
  const look =
    variant === "primary" ? "btn-primary" : "btn-ghost text-foreground disabled:opacity-40";
  return (
    <button type="button" className={`${base} ${look} ${className}`} {...props}>
      {/* 광택 의사요소가 글자를 덮지 않도록 내용만 위로 올린다. */}
      <span className="relative z-10 inline-flex items-center gap-2">{children}</span>
    </button>
  );
}

/** 섹션 위의 작은 라벨. 대문자 영문 + 자간으로 "제품" 느낌을 만든다. */
export function Kicker({ children }: { children: ReactNode }) {
  return (
    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-accent">{children}</p>
  );
}

export function SectionTitle({ children, hint }: { children: ReactNode; hint?: string }) {
  return (
    <div className="mb-3">
      <h2 className="text-base font-semibold tracking-tight">{children}</h2>
      {hint ? <p className="mt-1 text-xs leading-relaxed text-muted">{hint}</p> : null}
    </div>
  );
}

/** 숫자 하나를 크게 세우는 칸. 결과 요약 줄에서 조건을 보여줄 때 쓴다. */
export function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-xl border border-line bg-surface-muted/60 px-3 py-2">
      <p className="text-[10px] uppercase tracking-[0.14em] text-muted">{label}</p>
      <p className="mt-0.5 truncate text-sm font-semibold">{value}</p>
    </div>
  );
}

/**
 * 위저드 진행 표시. 어느 단계에 있고 몇 개가 남았는지 항상 보이게 한다.
 * 화면 위쪽에 고정으로 두면 4단계짜리 흐름이 한눈에 읽힌다.
 */
export function Stepper({ steps, current }: { steps: string[]; current: number }) {
  const progress = steps.length > 1 ? (current / (steps.length - 1)) * 100 : 0;

  return (
    <div className="relative">
      <div className="absolute left-0 right-0 top-4 h-px bg-line" aria-hidden />
      <div
        aria-hidden
        className="absolute left-0 top-4 h-px bg-gradient-to-r from-accent to-accent-2 transition-[width] duration-700 ease-out"
        style={{ width: `${progress}%` }}
      />
      <ol className="relative flex justify-between">
        {steps.map((step, index) => {
          const done = index < current;
          const active = index === current;
          return (
            <li key={step} className="flex flex-1 flex-col items-center gap-2">
              <span
                aria-hidden
                className={`flex h-8 w-8 items-center justify-center rounded-full border text-xs font-semibold transition-colors duration-500 ${
                  done
                    ? "border-accent/50 bg-accent text-accent-ink"
                    : active
                      ? "pulse-ring border-accent bg-accent-soft text-accent"
                      : "border-line bg-surface text-muted"
                }`}
              >
                {done ? "✓" : index + 1}
              </span>
              <span
                className={`text-center text-[11px] leading-tight sm:text-xs ${
                  active ? "font-semibold text-foreground" : "text-muted"
                }`}
              >
                {/* 현재 단계는 스크린 리더에도 알린다. */}
                {active ? <span className="sr-only">현재 단계: </span> : null}
                {step}
              </span>
            </li>
          );
        })}
      </ol>
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
      className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-semibold ${styles[status]}`}
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
      className={`inline-flex shrink-0 items-center rounded-md border px-2 py-0.5 text-[11px] font-semibold ${styles[severity]}`}
    >
      {SEVERITY_LABELS[severity]}
    </span>
  );
}

/** 고객 청중일 때 결과 상단에 띄우는 배지 (docs/07-frontend-ux.md). */
export function PublicReviewBadge() {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-lg border border-accent/40 bg-accent-soft px-2.5 py-1 text-xs font-semibold text-accent">
      <span aria-hidden>⚑</span>
      공개 전 검토 필요
    </span>
  );
}

export function ErrorNotice({ message }: { message: string }) {
  return (
    <div
      role="alert"
      className="flex items-start gap-2.5 rounded-xl border border-danger/30 bg-danger-soft px-4 py-3 text-sm text-danger"
    >
      <span aria-hidden className="mt-px">
        ⚠
      </span>
      <span className="leading-relaxed">{message}</span>
    </div>
  );
}
