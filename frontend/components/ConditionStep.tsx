"use client";

import type {
  Audience,
  DurationMinutes,
  PresentationRequest,
  Purpose,
  Style,
} from "@/lib/types";
import {
  AUDIENCE_HINTS,
  AUDIENCE_LABELS,
  DURATION_LABELS,
  PURPOSE_LABELS,
  RECOMMENDED_SLIDES,
  STYLE_LABELS,
} from "@/lib/labels";
import { Button, Card, Kicker } from "./ui";

const AUDIENCES = Object.keys(AUDIENCE_LABELS) as Audience[];
const PURPOSES = Object.keys(PURPOSE_LABELS) as Purpose[];
const STYLES = Object.keys(STYLE_LABELS) as Style[];
const DURATIONS: DurationMinutes[] = [3, 5, 10];

/** 생성 전에 장수가 어떻게 달라지는지 미리 보여 준다.
 *
 * 규칙의 원본은 백엔드 `planner._DURATION_SLIDES` / `_AUDIENCE_SLIDE_DELTA` 다. 여기 값은
 * 미리보기 전용 사본이라 실제 결과가 아니라 "예상"으로만 표기한다.
 */
const BASE_SLIDES: Record<DurationMinutes, number> = { 3: 4, 5: 5, 10: 7 };
const AUDIENCE_DELTA: Record<Audience, number> = {
  newcomer: 1,
  practitioner: 1,
  executive: -1,
  customer: 0,
};

function previewSlideCount(request: PresentationRequest): number {
  if (request.slide_count) return Math.max(3, Math.min(10, request.slide_count));
  const base = BASE_SLIDES[request.duration_minutes] ?? 5;
  return Math.max(3, Math.min(10, base + AUDIENCE_DELTA[request.audience]));
}

function Choice<T extends string | number>({
  options,
  value,
  onChange,
  label,
  hint,
  columns = 2,
}: {
  options: { value: T; label: string; hint?: string }[];
  value: T;
  onChange: (next: T) => void;
  label: string;
  hint?: string;
  columns?: 2 | 3;
}) {
  return (
    <fieldset>
      <legend className="text-sm font-semibold">{label}</legend>
      {hint ? <p className="mt-1 text-xs text-muted">{hint}</p> : null}
      <div
        className={`mt-3 grid gap-2.5 ${columns === 3 ? "sm:grid-cols-3" : "sm:grid-cols-2"}`}
      >
        {options.map((option) => {
          const selected = option.value === value;
          return (
            <button
              key={String(option.value)}
              type="button"
              aria-pressed={selected}
              onClick={() => onChange(option.value)}
              className={`group relative overflow-hidden rounded-xl border px-4 py-3 text-left transition-all duration-300 ${
                selected
                  ? "border-accent bg-accent-soft shadow-[0_12px_30px_-18px_rgba(255,138,61,0.9)]"
                  : "border-line bg-surface-glass hover:-translate-y-0.5 hover:border-line-strong hover:bg-surface-muted"
              }`}
            >
              <span className="flex items-start justify-between gap-2">
                <span className="block text-sm font-semibold">{option.label}</span>
                <span
                  aria-hidden
                  className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border text-[10px] transition-colors ${
                    selected
                      ? "border-accent bg-accent text-accent-ink"
                      : "border-line text-transparent"
                  }`}
                >
                  ✓
                </span>
              </span>
              {option.hint ? (
                <span className="mt-1 block text-xs leading-relaxed text-muted">{option.hint}</span>
              ) : null}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}

export function ConditionStep({
  request,
  keywordText,
  onChange,
  onKeywordTextChange,
  onBack,
  onSubmit,
}: {
  request: PresentationRequest;
  keywordText: string;
  onChange: (next: PresentationRequest) => void;
  onKeywordTextChange: (next: string) => void;
  onBack: () => void;
  onSubmit: () => void;
}) {
  function patch(partial: Partial<PresentationRequest>) {
    onChange({ ...request, ...partial });
  }

  const preview = previewSlideCount(request);
  const inputClass =
    "mt-2 w-full rounded-xl border border-line bg-surface-muted/60 px-3.5 py-2.5 text-sm outline-none transition-colors placeholder:text-muted/60 focus:border-accent";

  return (
    <div className="space-y-4">
      <Card className="space-y-7 p-6 sm:p-8">
        <div>
          <Kicker>Step 02</Kicker>
          <h2 className="mt-2 text-xl font-bold tracking-tight">발표 조건</h2>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            조건이 바뀌면 표현만이 아니라 담을 내용과 순서, 장수까지 다시 설계됩니다.
          </p>
        </div>

        <Choice
          label="청중"
          hint="가장 큰 차이를 만드는 조건입니다. 청중이 바뀌면 덱의 뼈대가 바뀝니다."
          value={request.audience}
          onChange={(audience) => patch({ audience })}
          options={AUDIENCES.map((audience) => ({
            value: audience,
            label: AUDIENCE_LABELS[audience],
            hint: AUDIENCE_HINTS[audience],
          }))}
        />

        {/* 조건을 바꾸는 즉시 장수가 움직이는 것을 보여 준다. */}
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-accent/25 bg-accent-soft px-4 py-3">
          <p className="text-xs leading-relaxed text-muted">
            <span className="font-semibold text-accent">
              {AUDIENCE_LABELS[request.audience]}
            </span>
            에게 {request.duration_minutes}분으로 발표할 때 예상 구성
          </p>
          <p aria-live="polite" className="text-sm font-bold">
            약 <span className="text-2xl tabular-nums text-accent">{preview}</span>장
          </p>
        </div>

        <Choice
          label="발표 목적"
          value={request.purpose}
          onChange={(purpose) => patch({ purpose })}
          options={PURPOSES.map((purpose) => ({
            value: purpose,
            label: PURPOSE_LABELS[purpose],
          }))}
        />

        <Choice
          label="발표 시간"
          columns={3}
          value={request.duration_minutes}
          onChange={(duration_minutes) => patch({ duration_minutes, slide_count: null })}
          options={DURATIONS.map((duration) => ({
            value: duration,
            label: DURATION_LABELS[duration],
            hint: RECOMMENDED_SLIDES[duration],
          }))}
        />

        <Choice
          label="표현 스타일"
          value={request.style}
          onChange={(style) => patch({ style })}
          options={STYLES.map((style) => ({ value: style, label: STYLE_LABELS[style] }))}
        />

        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label htmlFor="keywords" className="text-sm font-semibold">
              필수 키워드
            </label>
            <p className="mt-1 text-xs text-muted">쉼표로 구분해 입력하세요.</p>
            <input
              id="keywords"
              value={keywordText}
              onChange={(event) => onKeywordTextChange(event.target.value)}
              placeholder="정확도, 도입 효과"
              className={inputClass}
            />
          </div>

          <div>
            <label htmlFor="slide-count" className="text-sm font-semibold">
              슬라이드 수
            </label>
            <p className="mt-1 text-xs text-muted">
              비워 두면 시간과 청중에 맞춰 자동으로 정합니다.
            </p>
            <input
              id="slide-count"
              type="number"
              min={3}
              max={10}
              value={request.slide_count ?? ""}
              onChange={(event) =>
                patch({
                  slide_count: event.target.value === "" ? null : Number(event.target.value),
                })
              }
              placeholder={RECOMMENDED_SLIDES[request.duration_minutes]}
              className={inputClass}
            />
          </div>
        </div>

        <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-line bg-surface-muted/50 p-4 transition-colors hover:border-line-strong">
          <input
            type="checkbox"
            checked={request.preserve_original_terms}
            onChange={(event) => patch({ preserve_original_terms: event.target.checked })}
            className="mt-0.5 h-4 w-4 accent-[var(--accent)]"
          />
          <span>
            <span className="block text-sm font-semibold">원어 유지</span>
            <span className="mt-0.5 block text-xs leading-relaxed text-muted">
              켜면 원문의 영문 용어를 그대로 두고 괄호로 설명을 덧붙입니다.
            </span>
          </span>
        </label>
      </Card>

      <div className="flex flex-wrap justify-between gap-2">
        <Button onClick={onBack}>
          <span aria-hidden>←</span> 문서 다시 선택
        </Button>
        <Button variant="primary" onClick={onSubmit} className="px-6">
          발표자료 생성 <span aria-hidden>→</span>
        </Button>
      </div>
    </div>
  );
}
