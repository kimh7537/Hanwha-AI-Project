"use client";

import { useEffect, useMemo, useState } from "react";

import { documentSlideUrl, presentationSlideUrl } from "@/lib/api";
import type { GenerateResponse, PageContent, Slide } from "@/lib/types";

/**
 * 원본 문서와 생성된 발표자료를 슬라이드 단위로 나란히 놓는 전체 화면 비교.
 *
 * 양쪽 모두 실제 PPTX 를 렌더링한 슬라이드 이미지다. 왼쪽은 업로드한 원본 파일, 오른쪽은
 * 내려받게 될 결과 파일을 백엔드가 PowerPoint 로 구운 것이라, 표·도형·배경까지 눈으로 대조된다.
 * 렌더링이 안 되는 PC(PowerPoint 없음)나 PPTX 가 아닌 입력에서는 글자 비교로 되돌아간다.
 *
 * 짝짓기 규칙의 원본은 백엔드 `export_pptx._source_slide_index` 이며, 여기 사본은 화면 표시
 * 전용이다 — 즉 실제로 내려받는 PPTX 가 어떻게 얹히는지를 보여준다.
 *
 * 글자 비교의 원본 글은 chunk 가 아니라 `DocumentResponse.pages` 에서 온다. chunk 는 쪽 경계를
 * 넘어 묶이고 page 필드는 chunk 가 "시작한" 쪽이라, chunk 로 그리면 없는 장이 생기고 남의 글이 섞인다.
 *
 * X 로 닫으면 뒤의 결과 화면이 그대로 남아 있다.
 */
type Row =
  // number 는 발표용 덱에서 몇 번째 장인가 — 결과 슬라이드 이미지를 부르는 주소에 쓴다.
  | { kind: "rewritten"; page: number; original: string; slide: Slide; number: number }
  | { kind: "added"; slide: Slide; number: number }
  | { kind: "dropped"; page: number; original: string };

const KIND_LABELS: Record<Row["kind"], string> = {
  rewritten: "다시 씀",
  added: "새로 구성",
  dropped: "제외됨",
};

export function SourceCompare({
  result,
  pages,
  onClose,
}: {
  result: GenerateResponse;
  pages: PageContent[];
  onClose: () => void;
}) {
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const isPptx = result.document.filename.toLowerCase().endsWith(".pptx");
  const unitLabel = (page: number) => (isPptx ? `원본 슬라이드 ${page}` : `원문 ${page}쪽`);

  // 원본 슬라이드 이미지는 업로드가 PPTX 였을 때만 만들 수 있다. PDF·TXT 는 글자 비교뿐이다.
  const [showText, setShowText] = useState(false);
  const imageMode = isPptx && !showText;

  const rows = useMemo(() => {
    // 왼쪽에 그릴 원본 글. 파싱한 쪽 그대로라 "원본 슬라이드 N" 이 실제 N 장과 같다.
    const byPage = new Map<number, string>();
    for (const page of pages) byPage.set(page.page, page.text);

    // chunk id -> 그 chunk 가 시작한 쪽. 짝짓기에만 쓴다 (백엔드 export 와 같은 기준).
    const pageOf = new Map<string, number>();
    for (const item of result.source_analysis.source_evidence) pageOf.set(item.id, item.page);

    const used = new Set<number>();
    const paired: Row[] = result.slide_deck.slides.map((slide, index) => {
      const counts = new Map<number, number>();
      for (const ref of slide.source_refs) {
        const page = pageOf.get(ref);
        if (page !== undefined) counts.set(page, (counts.get(page) ?? 0) + 1);
      }
      // 근거를 가장 많이 끌어온 원본 슬라이드에 붙인다. 이미 쓴 원본은 건너뛴다.
      const page = [...counts.entries()]
        .sort((a, b) => b[1] - a[1])
        .find(([candidate]) => !used.has(candidate) && byPage.has(candidate))?.[0];

      const number = index + 1;
      if (page === undefined) return { kind: "added", slide, number };
      used.add(page);
      return { kind: "rewritten", page, original: byPage.get(page) ?? "", slide, number };
    });

    // 짝이 없는 원본도 빠짐없이 보여준다. 실제 PPTX 에서 빠지는 장이 여기서 드러난다.
    const dropped: Row[] = pages
      .filter((page) => !used.has(page.page))
      .map((page) => ({ kind: "dropped", page: page.page, original: page.text }));

    return [...paired, ...dropped];
  }, [result, pages]);

  const tally = (kind: Row["kind"]) => rows.filter((row) => row.kind === kind).length;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="원본과 결과 비교"
      className="animate-in fixed inset-0 z-50 overflow-y-auto bg-background/95 backdrop-blur-md"
    >
      <div className="glass sticky top-0 z-10 border-b border-line px-4 py-3 sm:px-6">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-base font-bold tracking-tight sm:text-lg">원본과 결과 비교</h2>
            <p className="mt-0.5 truncate text-[11px] text-muted">
              {result.document.filename} · 원본 {pages.length}
              {isPptx ? "장" : "쪽"} → 발표용 {result.slide_deck.slides.length}장
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="hidden gap-1.5 text-[11px] text-muted sm:flex">
              <Chip>다시 씀 {tally("rewritten")}</Chip>
              <Chip>새로 구성 {tally("added")}</Chip>
              <Chip>제외됨 {tally("dropped")}</Chip>
            </span>
            {isPptx ? (
              <button
                type="button"
                onClick={() => setShowText((value) => !value)}
                aria-pressed={showText}
                className="btn-ghost rounded-xl px-3 py-1.5 text-[11px] font-semibold"
              >
                {showText ? "슬라이드로 보기" : "글자로 보기"}
              </button>
            ) : null}
            <button
              type="button"
              onClick={onClose}
              aria-label="비교 닫기"
              className="btn-ghost flex h-9 w-9 items-center justify-center rounded-xl text-lg leading-none text-muted"
            >
              <span aria-hidden>✕</span>
            </button>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-6xl space-y-3 px-4 py-5 sm:px-6">
        <p className="rounded-xl border border-line bg-surface-muted/40 px-4 py-3 text-xs leading-relaxed text-muted">
          왼쪽은 업로드한 원본, 오른쪽은 청중에 맞춰 다시 설계한 결과입니다.{" "}
          {imageMode ? "두 파일을 실제로 렌더링한 슬라이드 이미지입니다. " : null}사실은 그대로
          두고 무엇을 넣고 뺄지·어떤 순서로 둘지가 바뀝니다. 발표 시간에 맞추느라 짝이 없는 원본은{" "}
          <strong className="text-foreground">제외됨</strong>으로 표시됩니다.
        </p>

        {rows.map((row, index) => (
          <div
            key={index}
            style={{ animationDelay: `${Math.min(index, 8) * 0.04}s` }}
            className="animate-in glass grid gap-3 rounded-2xl border border-line p-4 md:grid-cols-2"
          >
            <Side
              label={row.kind === "added" ? "원본에 짝이 없음" : unitLabel(row.page)}
              kind={row.kind}
              muted
            >
              {row.kind === "added" ? (
                <p className="text-xs leading-relaxed text-muted">
                  원문 전체에서 근거를 모아 새로 만든 슬라이드입니다.
                </p>
              ) : imageMode ? (
                <SlideImage
                  src={documentSlideUrl(result.document.document_id, row.page)}
                  alt={`원본 ${row.page}번째 슬라이드`}
                  fallback={<OriginalText text={row.original} />}
                />
              ) : (
                <OriginalText text={row.original} />
              )}
            </Side>

            <Side
              label={row.kind === "dropped" ? "발표자료에 없음" : "발표용 슬라이드"}
              kind={row.kind}
            >
              {row.kind === "dropped" ? (
                <p className="text-xs leading-relaxed text-muted">
                  이 원본은 발표 시간과 청중에 맞추는 과정에서 빠졌습니다. 내려받는 PPTX 에도
                  들어가지 않습니다.
                </p>
              ) : imageMode ? (
                <SlideImage
                  src={presentationSlideUrl(result.presentation_id, row.number)}
                  alt={`발표용 ${row.number}번째 슬라이드`}
                  fallback={<SlideText slide={row.slide} />}
                />
              ) : (
                <SlideText slide={row.slide} />
              )}
            </Side>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * 백엔드가 구운 슬라이드 PNG 한 장. 실패하면 조용히 글자 비교로 되돌아간다.
 *
 * PowerPoint 가 없는 PC 에서는 503 이 온다 — 렌더링이 없다고 화면이 비면 안 된다.
 * next/image 를 쓰지 않는 이유: 주소가 백엔드 오리진이라 remotePatterns 설정이 필요하고,
 * 원본을 그대로 보여주는 것이 목적이라 최적화·리사이즈가 오히려 방해된다.
 */
function SlideImage({
  src,
  alt,
  fallback,
}: {
  src: string;
  alt: string;
  fallback: React.ReactNode;
}) {
  const [state, setState] = useState<"loading" | "ready" | "failed">("loading");

  if (state === "failed") return <>{fallback}</>;

  return (
    <div className="relative aspect-video overflow-hidden rounded-xl border border-line bg-white">
      {state === "loading" ? (
        // 첫 장은 PowerPoint 를 띄우느라 몇 초 걸린다. 무슨 일이 일어나는지 글로 알린다.
        <p className="absolute inset-0 flex items-center justify-center px-4 text-center text-[11px] text-muted">
          슬라이드 이미지를 만드는 중입니다…
        </p>
      ) : null}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={alt}
        width={1280}
        height={720}
        loading="lazy"
        onLoad={() => setState("ready")}
        onError={() => setState("failed")}
        className={`h-full w-full object-contain transition-opacity duration-200 ${
          state === "ready" ? "opacity-100" : "opacity-0"
        }`}
      />
    </div>
  );
}

function OriginalText({ text }: { text: string }) {
  if (!text.trim()) {
    return (
      <p className="text-xs leading-relaxed text-muted">
        글이 없는 장입니다 (이미지·표만 있는 원본).
      </p>
    );
  }
  return <p className="whitespace-pre-wrap text-xs leading-relaxed text-muted">{text}</p>;
}

function SlideText({ slide }: { slide: Slide }) {
  return (
    <>
      <h3 className="text-sm font-bold leading-snug">{slide.title}</h3>
      {slide.takeaway ? (
        <p className="mt-2 border-l-2 border-accent bg-accent-soft px-3 py-2 text-xs leading-relaxed">
          {slide.takeaway}
        </p>
      ) : null}
      <ul className="mt-2 space-y-1.5">
        {slide.bullets.map((bullet) => (
          <li key={bullet} className="flex gap-2 text-xs leading-relaxed">
            <span aria-hidden className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-accent" />
            {bullet}
          </li>
        ))}
      </ul>
    </>
  );
}

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-lg border border-line bg-surface-muted/60 px-2 py-1">{children}</span>
  );
}

function Side({
  label,
  kind,
  muted = false,
  children,
}: {
  label: string;
  kind: Row["kind"];
  muted?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className={`rounded-xl border border-line p-3.5 ${muted ? "bg-surface-muted/30" : ""}`}>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
          {label}
        </span>
        {/* 상태는 색만이 아니라 글자로도 읽혀야 한다. */}
        <span
          className={`rounded-md border px-1.5 py-0.5 text-[10px] font-semibold ${
            kind === "dropped"
              ? "border-warn/40 bg-warn-soft text-warn"
              : kind === "added"
                ? "border-ok/40 bg-ok-soft text-ok"
                : "border-accent/40 bg-accent-soft text-accent"
          }`}
        >
          {KIND_LABELS[kind]}
        </span>
      </div>
      {children}
    </div>
  );
}
