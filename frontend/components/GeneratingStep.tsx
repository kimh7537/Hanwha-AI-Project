"use client";

import { PIPELINE_STEPS } from "@/lib/labels";
import { Card, ErrorNotice } from "./ui";

/**
 * 생성 5단계 표시. 진행 상태는 실제 API 호출 진행도를 그대로 반영한다
 * (docs/07-frontend-ux.md).
 */
export function GeneratingStep({
  activeIndex,
  error,
  onRetry,
  onBack,
}: {
  activeIndex: number;
  error: string | null;
  onRetry: () => void;
  onBack: () => void;
}) {
  return (
    <Card className="p-6">
      <h2 className="text-base font-semibold">3. 생성 중</h2>
      <p className="mt-1 text-sm text-muted">
        원문에서 사실을 뽑고, 청중에 맞춰 다시 쓰고, 원문과 대조합니다.
      </p>

      <ol className="mt-6 space-y-3">
        {PIPELINE_STEPS.map((step, index) => {
          const done = index < activeIndex;
          const active = index === activeIndex && !error;
          const failed = index === activeIndex && Boolean(error);

          return (
            <li key={step} className="flex items-center gap-3">
              <span
                aria-hidden
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-[11px] font-semibold ${
                  done
                    ? "border-ok/40 bg-ok-soft text-ok"
                    : failed
                      ? "border-danger/40 bg-danger-soft text-danger"
                      : active
                        ? "border-accent bg-accent-soft text-accent"
                        : "border-line bg-surface-muted text-muted"
                }`}
              >
                {done ? "✓" : failed ? "✕" : index + 1}
              </span>
              <span
                className={`text-sm ${
                  done || active ? "font-medium" : "text-muted"
                }`}
              >
                {step}
              </span>
              {active ? <span className="text-xs text-accent">진행 중…</span> : null}
            </li>
          );
        })}
      </ol>

      {error ? (
        <div className="mt-6 space-y-3">
          <ErrorNotice message={error} />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onRetry}
              className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white hover:opacity-90"
            >
              다시 시도
            </button>
            <button
              type="button"
              onClick={onBack}
              className="rounded-md border border-line bg-surface px-4 py-2 text-sm hover:bg-surface-muted"
            >
              조건 수정
            </button>
          </div>
        </div>
      ) : null}
    </Card>
  );
}
