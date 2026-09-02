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
import { Card } from "./ui";

const AUDIENCES = Object.keys(AUDIENCE_LABELS) as Audience[];
const PURPOSES = Object.keys(PURPOSE_LABELS) as Purpose[];
const STYLES = Object.keys(STYLE_LABELS) as Style[];
const DURATIONS: DurationMinutes[] = [3, 5, 10];

function Choice<T extends string | number>({
  options,
  value,
  onChange,
  label,
}: {
  options: { value: T; label: string; hint?: string }[];
  value: T;
  onChange: (next: T) => void;
  label: string;
}) {
  return (
    <fieldset>
      <legend className="text-sm font-medium">{label}</legend>
      <div className="mt-2 grid gap-2 sm:grid-cols-2">
        {options.map((option) => {
          const selected = option.value === value;
          return (
            <button
              key={String(option.value)}
              type="button"
              aria-pressed={selected}
              onClick={() => onChange(option.value)}
              className={`rounded-md border px-3 py-2 text-left transition-colors ${
                selected
                  ? "border-accent bg-accent-soft"
                  : "border-line bg-surface hover:bg-surface-muted"
              }`}
            >
              <span className="block text-sm font-medium">{option.label}</span>
              {option.hint ? (
                <span className="mt-0.5 block text-xs text-muted">{option.hint}</span>
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

  return (
    <div className="space-y-4">
      <Card className="space-y-6 p-6">
        <div>
          <h2 className="text-base font-semibold">2. 발표 조건</h2>
          <p className="mt-1 text-sm text-muted">
            같은 문서라도 조건에 따라 설명의 깊이와 표현이 달라집니다.
          </p>
        </div>

        <Choice
          label="청중"
          value={request.audience}
          onChange={(audience) => patch({ audience })}
          options={AUDIENCES.map((audience) => ({
            value: audience,
            label: AUDIENCE_LABELS[audience],
            hint: AUDIENCE_HINTS[audience],
          }))}
        />

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

        <div className="grid gap-6 sm:grid-cols-2">
          <div>
            <label htmlFor="keywords" className="text-sm font-medium">
              필수 키워드
            </label>
            <p className="mt-1 text-xs text-muted">쉼표로 구분해 입력하세요.</p>
            <input
              id="keywords"
              value={keywordText}
              onChange={(event) => onKeywordTextChange(event.target.value)}
              placeholder="정확도, 도입 효과"
              className="mt-2 w-full rounded-md border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-accent"
            />
          </div>

          <div>
            <label htmlFor="slide-count" className="text-sm font-medium">
              슬라이드 수
            </label>
            <p className="mt-1 text-xs text-muted">
              비워 두면 발표 시간에 맞춰 자동으로 정합니다.
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
              className="mt-2 w-full rounded-md border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-accent"
            />
          </div>
        </div>

        <label className="flex items-start gap-3 rounded-md border border-line bg-surface-muted p-3">
          <input
            type="checkbox"
            checked={request.preserve_original_terms}
            onChange={(event) => patch({ preserve_original_terms: event.target.checked })}
            className="mt-0.5 accent-[var(--accent)]"
          />
          <span>
            <span className="block text-sm font-medium">원어 유지</span>
            <span className="mt-0.5 block text-xs text-muted">
              켜면 원문의 영문 용어를 그대로 두고 괄호로 설명을 덧붙입니다.
            </span>
          </span>
        </label>
      </Card>

      <div className="flex justify-between">
        <button
          type="button"
          onClick={onBack}
          className="rounded-md border border-line bg-surface px-4 py-2 text-sm transition-colors hover:bg-surface-muted"
        >
          ← 문서 다시 선택
        </button>
        <button
          type="button"
          onClick={onSubmit}
          className="rounded-md bg-accent px-5 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90"
        >
          발표자료 생성
        </button>
      </div>
    </div>
  );
}
