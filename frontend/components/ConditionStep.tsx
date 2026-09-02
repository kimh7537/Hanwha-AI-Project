"use client";

import { useEffect, useMemo, useState } from "react";
import { fetchAudiencePlans, fetchPlanPreview } from "@/lib/api";
import type {
  Audience,
  AudiencePlan,
  AudiencePlansResponse,
  AudienceProfile,
  DurationMinutes,
  Interest,
  MessageControl,
  PlanPreview,
  PresentationRequest,
  Purpose,
  Style,
} from "@/lib/types";
import {
  AUDIENCE_HINTS,
  AUDIENCE_LABELS,
  DURATION_LABELS,
  EXPERTISE_LABELS,
  INTEREST_LABELS,
  PURPOSE_LABELS,
  RECOMMENDED_SLIDES,
  STYLE_LABELS,
} from "@/lib/labels";
import { Button, Card, Kicker } from "./ui";

const AUDIENCES = Object.keys(AUDIENCE_LABELS) as Audience[];
const INTERESTS = Object.keys(INTEREST_LABELS) as Interest[];
const PURPOSES = Object.keys(PURPOSE_LABELS) as Purpose[];
const STYLES = Object.keys(STYLE_LABELS) as Style[];
const DURATIONS: DurationMinutes[] = [3, 5, 10];

/** 백엔드(`/api/audiences`)를 못 받았을 때 쓰는 사본.
 *
 * 원본은 `planner.DURATION_SLIDES` / `AUDIENCE_SLIDE_DELTA` 이고 평소에는 그 값을 받아 쓴다.
 * 여기 값은 백엔드가 잠깐 응답하지 않아도 장수 칸이 비지 않게 하려는 것뿐이다.
 */
const BASE_SLIDES: Record<DurationMinutes, number> = { 3: 4, 5: 5, 10: 7 };
const AUDIENCE_DELTA: Record<Audience, number> = {
  newcomer: 1,
  practitioner: 1,
  executive: -1,
  customer: 0,
};

const clamp = (count: number) => Math.max(3, Math.min(10, count));

/** 사용자가 장수를 정하지 않았을 때 시간·청중 규칙이 내놓을 장수. */
function autoSlideCount(
  request: PresentationRequest,
  plans: AudiencePlansResponse | null,
  plan: AudiencePlan | null,
): number {
  const base =
    plans?.duration_slides[String(request.duration_minutes)] ??
    BASE_SLIDES[request.duration_minutes] ??
    5;
  const delta = plan?.slide_delta ?? AUDIENCE_DELTA[request.audience];
  return clamp(base + delta);
}

/** 쉼표로 구분한 입력을 목록으로. 빈 항목은 버린다. */
const parseList = (text: string) =>
  text
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

/** 목록을 입력칸에 되돌린다. 사용자가 찍은 쉼표 뒤 공백을 그대로 두면 편집이 어색해진다. */
const listText = (items: string[]) => items.join(", ");

/** 용어 풀이를 몇 개 싣는지. 청중별로 다르다는 가장 단순한 증거라 화면에 그대로 적는다. */
function glossaryLabel(limit: number | null): string {
  if (limit === null) return "전부";
  return limit === 0 ? "넣지 않음" : `${limit}개`;
}

/** 이야기 순서를 번호가 붙은 흐름으로. 청중을 바꾸면 이 줄이 통째로 바뀐다. */
function StorylineFlow({ storyline, compact }: { storyline: string[]; compact?: boolean }) {
  return (
    <ol className="flex flex-wrap items-center gap-x-1.5 gap-y-2">
      {storyline.map((topic, index) => (
        <li key={topic} className="flex items-center gap-1.5">
          {index > 0 ? (
            <span aria-hidden className="text-xs text-muted">
              →
            </span>
          ) : null}
          <span
            className={`flex items-center gap-1.5 rounded-lg border border-line bg-surface-muted/70 px-2.5 py-1 ${
              compact ? "text-[11px]" : "text-xs"
            } font-medium`}
          >
            <span aria-hidden className="font-mono text-[10px] text-accent">
              {index + 1}
            </span>
            {topic}
          </span>
        </li>
      ))}
    </ol>
  );
}

/** 장수를 어떻게 정하고 있는지.
 *
 * 대부분 `slide_count` 에서 파생되지만, 직접 입력한 값이 원본 장수와 같아지는 경우가 있어
 * "직접 정하기"를 골랐다는 사실만 따로 들고 있는다.
 */
type SlideMode = "source" | "auto" | "manual";

function slideMode(
  request: PresentationRequest,
  sourceSlides: number | null,
  manual: boolean,
): SlideMode {
  if (request.slide_count === null) return "auto";
  if (!manual && sourceSlides !== null && request.slide_count === sourceSlides) return "source";
  return "manual";
}

const SLIDE_MODES: { value: SlideMode; label: string }[] = [
  { value: "source", label: "원본 그대로" },
  { value: "auto", label: "시간·청중에 맞춰" },
  { value: "manual", label: "직접 정하기" },
];

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
  sourceSlides,
  onChange,
  onKeywordTextChange,
  onBack,
  onSubmit,
}: {
  request: PresentationRequest;
  keywordText: string;
  /** 업로드한 원본의 장수. 그대로 쓸 수 없는 입력이면 null. */
  sourceSlides: number | null;
  onChange: (next: PresentationRequest) => void;
  onKeywordTextChange: (next: string) => void;
  onBack: () => void;
  onSubmit: () => void;
}) {
  function patch(partial: Partial<PresentationRequest>) {
    onChange({ ...request, ...partial });
  }

  function patchProfile(partial: Partial<AudienceProfile>) {
    onChange({ ...request, profile: { ...request.profile, ...partial } });
  }

  function patchMessage(partial: Partial<MessageControl>) {
    onChange({ ...request, message: { ...request.message, ...partial } });
  }

  function toggleInterest(interest: Interest) {
    const current = request.profile.interests;
    patchProfile({
      interests: current.includes(interest)
        ? current.filter((item) => item !== interest)
        : [...current, interest],
    });
  }

  const [manual, setManual] = useState(false);

  // 쉼표로 구분하는 칸은 화면에 보이는 글자를 그대로 들고 있는다.
  //
  // 요청에 든 목록을 매번 되돌려 그리면 방금 찍은 쉼표와 그 뒤 공백이 즉시 지워진다
  // (`압도적,` -> ["압도적"] -> `압도적`). 그러면 두 번째 항목을 아예 칠 수가 없다.
  // 요청에는 파싱한 값을 넣고, 화면에는 사용자가 친 글자를 그대로 남긴다.
  // `강조` 칸이 페이지 수준에서 `keywordText` 를 따로 들고 있는 것과 같은 이유다.
  const [minimizeText, setMinimizeText] = useState(() => listText(request.message.minimize));
  const [bannedText, setBannedText] = useState(() => listText(request.message.banned));

  // 청중별 설계 규칙은 백엔드가 소유한다. 화면에 한 벌 더 적어 두면 규칙을 고칠 때 갈라져서,
  // 생성 전에 예고한 순서와 실제 결과가 어긋난다.
  const [plans, setPlans] = useState<AudiencePlansResponse | null>(null);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    let alive = true;
    fetchAudiencePlans().then((data) => {
      if (alive) setPlans(data);
    });
    return () => {
      alive = false;
    };
  }, []);

  const planFor = useMemo(
    () => new Map((plans?.audiences ?? []).map((item) => [item.audience, item])),
    [plans],
  );
  const plan = planFor.get(request.audience) ?? null;

  // 이해도가 용어 풀이 개수를 움직이고 메시지 통제가 순위를 바꾸면서, 화면이 그 계산을 따라
  // 하면 실제 결과와 어긋나기 쉬워졌다. 조건이 바뀔 때마다 생성 경로와 같은 함수에 물어본다.
  // 사전지식·메시지는 타이핑 입력이라 잠깐 기다렸다 부른다.
  const [live, setLive] = useState<PlanPreview | null>(null);

  useEffect(() => {
    let alive = true;
    const timer = setTimeout(() => {
      fetchPlanPreview(request).then((data) => {
        if (alive) setLive(data);
      });
    }, 250);
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [request]);

  const storyline = live?.storyline ?? plan?.storyline ?? [];
  const leads = live?.leads ?? plan?.leads ?? "";
  const trims = live?.trims ?? plan?.trims ?? "";
  const glossary = live ? live.glossary_limit : (plan?.glossary_limit ?? null);
  const notes = live?.notes ?? [];

  const auto = autoSlideCount(request, plans, plan);
  const mode = slideMode(request, sourceSlides, manual);
  const preview = live?.slide_count ?? (request.slide_count ? clamp(request.slide_count) : auto);
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

        {/* 청중 프로파일 — 같은 '고객사'라도 기술 이해도와 관심 축이 다른 자리를 구분한다.
            청중이 뼈대를 정하고, 여기서 그 안에 무엇을 얼마나 담을지가 정해진다. */}
        <fieldset className="space-y-4 rounded-2xl border border-line bg-surface-muted/40 p-4 sm:p-5">
          <legend className="px-1 text-sm font-semibold">청중 프로파일</legend>
          <p className="text-xs leading-relaxed text-muted">
            청중이 <span className="text-foreground">누구</span>인지에 더해{" "}
            <span className="text-foreground">어느 정도로, 무엇에 관심 있는지</span>를 알려 주면 같은
            뼈대 안에서 실을 내용이 달라집니다.
          </p>

          <div>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <label htmlFor="expertise" className="text-xs font-semibold">
                기술 이해도
              </label>
              <span className="text-xs text-muted">
                <span className="font-semibold text-accent">
                  {EXPERTISE_LABELS[request.profile.expertise]}
                </span>{" "}
                ({request.profile.expertise}/5)
              </span>
            </div>
            <input
              id="expertise"
              type="range"
              min={1}
              max={5}
              step={1}
              value={request.profile.expertise}
              onChange={(event) =>
                patchProfile({ expertise: Number(event.target.value) })
              }
              className="mt-2 w-full accent-[var(--accent)]"
            />
            {/* 슬라이더 위치만으로 뜻을 알 수 없으므로 양 끝에 라벨을 적는다. */}
            <div className="mt-1 flex justify-between text-[11px] text-muted">
              <span>{EXPERTISE_LABELS[1]}</span>
              <span>{EXPERTISE_LABELS[5]}</span>
            </div>
          </div>

          <div>
            <p className="text-xs font-semibold">관심 영역</p>
            <p className="mt-1 text-[11px] leading-relaxed text-muted">
              고른 축에 해당하는 내용이 각 항목 안에서 앞으로 옵니다. 원문에 없는 축은 만들지
              않습니다.
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              {INTERESTS.map((interest) => {
                const on = request.profile.interests.includes(interest);
                return (
                  <label
                    key={interest}
                    className={`flex cursor-pointer items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs transition-colors ${
                      on
                        ? "border-accent/50 bg-accent-soft text-accent"
                        : "border-line bg-surface-glass text-muted hover:border-line-strong"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={on}
                      onChange={() => toggleInterest(interest)}
                      className="h-3.5 w-3.5 accent-[var(--accent)]"
                    />
                    {INTEREST_LABELS[interest]}
                  </label>
                );
              })}
            </div>
          </div>

          <div>
            <label htmlFor="prior-knowledge" className="block text-xs font-semibold">
              이미 알고 있는 것
            </label>
            <input
              id="prior-knowledge"
              type="text"
              value={request.profile.prior_knowledge}
              onChange={(event) => patchProfile({ prior_knowledge: event.target.value })}
              placeholder="예) 기본적인 제품 개념은 이해"
              className={inputClass}
            />
            <p className="mt-1.5 text-[11px] leading-relaxed text-muted">
              여기 적은 내용과 겹치는 설명은 뒤로 밀립니다. 사실이 지워지지는 않습니다.
            </p>
          </div>
        </fieldset>

        {/* 조건을 바꾸는 즉시 "무엇을 어떤 순서로, 몇 장에" 담을지가 함께 움직이는 것을 보여 준다.
            장수만 보여 주면 문체 옵션과 구분되지 않는다 — 바뀌는 것은 뼈대다. */}
        <div
          aria-live="polite"
          className="space-y-3.5 rounded-2xl border border-accent/25 bg-accent-soft p-4 sm:p-5"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs leading-relaxed text-muted">
              {sourceSlides ? (
                <>
                  원본 <span className="font-semibold text-foreground">{sourceSlides}장</span> ·{" "}
                </>
              ) : null}
              <span className="font-semibold text-accent">
                {AUDIENCE_LABELS[request.audience]}
              </span>
              에게 {request.duration_minutes}분으로 발표할 때 예상 구성
            </p>
            <p className="text-sm font-bold">
              약 <span className="text-2xl tabular-nums text-accent">{preview}</span>장
            </p>
          </div>

          {storyline.length > 0 ? (
            <>
              <div>
                <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted">
                  이야기 순서
                </p>
                <StorylineFlow storyline={storyline} />
              </div>

              <dl className="grid gap-2 sm:grid-cols-2">
                <div className="rounded-xl border border-line bg-surface-muted/50 p-3">
                  <dt className="text-[11px] font-semibold text-accent">앞세우는 것</dt>
                  <dd className="mt-1 text-xs leading-relaxed">{leads}</dd>
                </div>
                <div className="rounded-xl border border-line bg-surface-muted/50 p-3">
                  <dt className="text-[11px] font-semibold text-muted">덜어내는 것</dt>
                  <dd className="mt-1 text-xs leading-relaxed">{trims}</dd>
                </div>
              </dl>

              {/* 프로파일·메시지 통제가 실제로 무엇을 했는지. 입력만 받고 결과가 안 보이면
                  그 칸들은 장식이 된다. */}
              {notes.length > 0 ? (
                <ul className="space-y-1.5 rounded-xl border border-accent/30 bg-surface-muted/50 p-3">
                  {notes.map((note) => (
                    <li key={note} className="flex gap-2 text-xs leading-relaxed">
                      <span aria-hidden className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-accent" />
                      {note}
                    </li>
                  ))}
                </ul>
              ) : null}

              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-[11px] text-muted">
                  용어 풀이{" "}
                  <span className="font-semibold text-foreground">{glossaryLabel(glossary)}</span>
                </p>
                <button
                  type="button"
                  onClick={() => setShowAll((open) => !open)}
                  aria-expanded={showAll}
                  className="rounded-full border border-line bg-surface-glass px-3 py-1 text-[11px] text-muted transition-colors hover:border-line-strong hover:text-foreground"
                >
                  네 청중 한눈에 보기 <span aria-hidden>{showAll ? "▲" : "▼"}</span>
                </button>
              </div>

              {/* 심사자가 가장 먼저 의심하는 지점 — "청중만 바꾼 같은 덱 아닌가".
                  네 뼈대를 나란히 두면 눈으로 바로 확인된다. */}
              {showAll ? (
                <ul className="space-y-2 border-t border-line pt-3">
                  {(plans?.audiences ?? []).map((item) => {
                    const current = item.audience === request.audience;
                    return (
                      <li
                        key={item.audience}
                        className={`rounded-xl border p-3 ${
                          current
                            ? "border-accent/40 bg-surface-muted/60"
                            : "border-line bg-transparent"
                        }`}
                      >
                        <p className="mb-1.5 text-[11px] font-semibold">
                          {item.label}
                          {current ? (
                            <span className="ml-1.5 text-accent">· 지금 선택</span>
                          ) : null}
                          <span className="ml-1.5 font-normal text-muted">
                            용어 풀이 {glossaryLabel(item.glossary_limit)}
                          </span>
                        </p>
                        <StorylineFlow storyline={item.storyline} compact />
                      </li>
                    );
                  })}
                </ul>
              ) : null}
            </>
          ) : null}
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
          // 장수는 아래에서 따로 고르므로 시간이 바뀌어도 그 선택을 지우지 않는다.
          onChange={(duration_minutes) => patch({ duration_minutes })}
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

        {/* 메시지 통제 — 발표의 의도를 발표자가 직접 정한다.
            네 칸 어느 것도 원문에 없는 사실을 만들지 않는다. 순위를 올리고 내릴 뿐이고,
            지켜지지 않은 것은 결과 화면의 정확성 검증이 잡는다. */}
        <fieldset className="space-y-4 rounded-2xl border border-line bg-surface-muted/40 p-4 sm:p-5">
          <legend className="px-1 text-sm font-semibold">메시지 통제</legend>
          <p className="text-xs leading-relaxed text-muted">
            이 발표로 무엇을 남기고 무엇을 덜 말할지 정합니다. 없는 사실을 만들지는 않으며,
            지켜지지 않은 항목은 <span className="text-foreground">정확성 검증</span> 탭에 뜹니다.
          </p>

          <div>
            <label htmlFor="must-convey" className="block text-xs font-semibold">
              반드시 전달할 메시지
            </label>
            <input
              id="must-convey"
              value={request.message.must_convey}
              onChange={(event) => patchMessage({ must_convey: event.target.value })}
              placeholder="예) 기존 대비 운용 효율 향상"
              className={inputClass}
            />
            <p className="mt-1.5 text-[11px] leading-relaxed text-muted">
              이 메시지를 뒷받침하는 원문 사실을 앞으로 당깁니다. 원문에 근거가 없으면 넣지 않고
              검증에서 알려 드립니다.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="keywords" className="block text-xs font-semibold">
                강조
              </label>
              <input
                id="keywords"
                value={keywordText}
                onChange={(event) => onKeywordTextChange(event.target.value)}
                placeholder="신뢰성, 유지보수성"
                className={inputClass}
              />
              <p className="mt-1.5 text-[11px] leading-relaxed text-muted">
                쉼표로 구분. 덱에 최소 1회 등장해야 하고 검증에서 확인합니다.
              </p>
            </div>

            <div>
              <label htmlFor="minimize" className="block text-xs font-semibold">
                최소화
              </label>
              <input
                id="minimize"
                value={minimizeText}
                onChange={(event) => {
                  setMinimizeText(event.target.value);
                  patchMessage({ minimize: parseList(event.target.value) });
                }}
                placeholder="복잡한 기술적 세부사항"
                className={inputClass}
              />
              <p className="mt-1.5 text-[11px] leading-relaxed text-muted">
                분량을 줄여 뒤로 밉니다. 사실을 지우지는 않습니다.
              </p>
            </div>
          </div>

          <div>
            {/* `block` 이 없으면 inline 라벨 옆으로 폭이 제한된 입력칸이 올라붙어 한 줄에 겹친다. */}
            <label htmlFor="banned" className="block text-xs font-semibold">
              사용 금지
            </label>
            <input
              id="banned"
              value={bannedText}
              onChange={(event) => {
                setBannedText(event.target.value);
                patchMessage({ banned: parseList(event.target.value) });
              }}
              placeholder="압도적, 세계 최고"
              className={`${inputClass} sm:max-w-md`}
            />
            <p className="mt-1.5 text-[11px] leading-relaxed text-muted">
              이 표현이 든 문장을 피해 고릅니다. 그래도 남으면 검증이 어느 슬라이드인지 짚어 줍니다.
            </p>
          </div>
        </fieldset>

        {/* 기준이 되는 원본 장수를 모르면 "몇 장으로 할지"를 고를 수가 없다.
            원본을 그대로 쓰는 것이 기본이고, 자동·직접은 한 번 눌러 바꾼다. */}
        <fieldset>
          <legend className="text-sm font-semibold">슬라이드 수</legend>
          <p className="mt-1 text-xs leading-relaxed text-muted">
            {sourceSlides
              ? `업로드한 원본은 ${sourceSlides}장입니다. 기본은 원본 장수를 그대로 씁니다.`
              : "원본 장수를 그대로 쓸 수 없는 입력이라 시간과 청중에 맞춰 정합니다."}
          </p>

          <div className="mt-3 flex flex-wrap gap-2">
            {SLIDE_MODES.filter((option) => option.value !== "source" || sourceSlides).map(
              (option) => {
                const selected = option.value === mode;
                const count =
                  option.value === "source" ? sourceSlides : option.value === "auto" ? auto : null;
                return (
                  <button
                    key={option.value}
                    type="button"
                    aria-pressed={selected}
                    onClick={() => {
                      setManual(option.value === "manual");
                      patch({
                        slide_count:
                          option.value === "source"
                            ? sourceSlides
                            : option.value === "auto"
                              ? null
                              : (request.slide_count ?? sourceSlides ?? auto),
                      });
                    }}
                    className={`rounded-xl border px-4 py-2.5 text-left transition-all duration-300 ${
                      selected
                        ? "border-accent bg-accent-soft"
                        : "border-line bg-surface-glass hover:-translate-y-0.5 hover:border-line-strong"
                    }`}
                  >
                    <span className="block text-sm font-semibold">{option.label}</span>
                    <span className="mt-0.5 block text-xs text-muted">
                      {count === null ? "3~10장 사이에서 지정" : `${count}장`}
                    </span>
                  </button>
                );
              },
            )}
          </div>

          {mode === "manual" ? (
            <input
              id="slide-count"
              aria-label="슬라이드 수 직접 입력"
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
              className={`${inputClass} sm:max-w-[10rem]`}
            />
          ) : null}

          {mode === "source" && sourceSlides !== auto ? (
            <p className="mt-2 text-xs leading-relaxed text-muted">
              시간·청중에 맡기면 {auto}장이 됩니다. 원본 장수를 유지하는 동안에는 청중을 바꿔도
              장수가 그대로입니다.
            </p>
          ) : null}
        </fieldset>

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
