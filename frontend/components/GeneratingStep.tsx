"use client";

import { PIPELINE_STEPS } from "@/lib/labels";
import { Button, Card, ErrorNotice, Kicker } from "./ui";

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
  const done = Math.min(activeIndex, PIPELINE_STEPS.length);
  const percent = Math.round((done / PIPELINE_STEPS.length) * 100);

  return (
    <Card className="p-6 sm:p-8">
      <Kicker>Step 03</Kicker>
      <div className="mt-2 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold tracking-tight">
            {error ? "생성을 멈췄습니다" : "청중에 맞춰 다시 설계하는 중"}
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            원문에서 사실을 뽑고, 청중에 맞춰 다시 쓰고, 원문과 대조합니다.
          </p>
        </div>
        <p aria-live="polite" className="text-3xl font-black tabular-nums text-accent">
          {percent}
          <span className="text-base font-bold">%</span>
        </p>
      </div>

      <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-surface-muted">
        <div
          className={`h-full rounded-full transition-[width] duration-700 ease-out ${
            error ? "bg-danger" : "bg-gradient-to-r from-accent to-accent-2"
          }`}
          style={{ width: `${Math.max(percent, 4)}%` }}
        />
      </div>

      <ol className="mt-7 space-y-2.5">
        {PIPELINE_STEPS.map((step, index) => {
          const finished = index < activeIndex;
          const active = index === activeIndex && !error;
          const failed = index === activeIndex && Boolean(error);

          return (
            <li
              key={step}
              style={{ animationDelay: `${index * 0.05}s` }}
              className={`animate-in flex items-center gap-3 rounded-xl border px-4 py-3 transition-colors duration-500 ${
                active
                  ? "border-accent/40 bg-accent-soft"
                  : failed
                    ? "border-danger/30 bg-danger-soft"
                    : "border-line bg-surface-muted/40"
              }`}
            >
              <span
                aria-hidden
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-[11px] font-semibold ${
                  finished
                    ? "border-ok/40 bg-ok-soft text-ok"
                    : failed
                      ? "border-danger/40 bg-danger-soft text-danger"
                      : active
                        ? "border-accent bg-accent text-accent-ink"
                        : "border-line bg-surface text-muted"
                }`}
              >
                {finished ? "✓" : failed ? "✕" : index + 1}
              </span>
              <span className={`text-sm ${finished || active ? "font-medium" : "text-muted"}`}>
                {step}
              </span>
              {active ? (
                <span className="ml-auto flex items-center gap-1.5 text-xs text-accent">
                  <span
                    aria-hidden
                    className="h-3 w-3 animate-spin rounded-full border-2 border-accent border-t-transparent"
                  />
                  진행 중
                </span>
              ) : null}
              {/* 아직 시작하지 않은 단계는 자리표시자로 남겨 화면이 비어 보이지 않게 한다. */}
              {!finished && !active && !failed ? (
                <span aria-hidden className="shimmer ml-auto h-2 w-16 rounded-full opacity-50" />
              ) : null}
            </li>
          );
        })}
      </ol>

      {error ? (
        <div className="mt-6 space-y-3">
          <ErrorNotice message={error} />
          <div className="flex flex-wrap gap-2">
            <Button variant="primary" onClick={onRetry}>
              다시 시도
            </Button>
            <Button onClick={onBack}>조건 수정</Button>
          </div>
        </div>
      ) : null}
    </Card>
  );
}
