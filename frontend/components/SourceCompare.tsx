"use client";

import { useEffect, useMemo, useState } from "react";

import {
  documentSlideUrl,
  fetchSlideDiff,
  fetchSourceMap,
  presentationSlideUrl,
  type DiffRegion,
  type SourceMap,
} from "@/lib/api";
import type { GenerateResponse, PageContent, Slide } from "@/lib/types";

/**
 * 원본 문서와 생성된 발표자료를 슬라이드 단위로 나란히 놓는 전체 화면 비교.
 *
 * **한 쌍씩 크게 본다.** 슬라이드 이미지를 여러 쌍 쌓아 놓으면 한 장이 손톱만 해져 무엇이
 * 달라졌는지 눈으로 잡히지 않는다. 위의 탭으로 장을 넘기고(← →) 화면에는 한 쌍만 크게 둔다.
 *
 * 양쪽 모두 실제 PPTX 를 렌더링한 슬라이드 이미지다. 왼쪽은 업로드한 원본 파일, 오른쪽은
 * 내려받게 될 결과 파일을 백엔드가 PowerPoint 로 구운 것이라, 표·도형·배경까지 눈으로 대조된다.
 * 그 두 그림을 백엔드가 픽셀로 대조해(`services/slide_diff.py`) 달라진 자리를 빨간 네모로 얹는다.
 * 좌표계가 같아서 네모 한 벌이 좌우 양쪽에 그대로 맞는다.
 *
 * 렌더링이 안 되는 PC(PowerPoint 없음)나 PPTX 가 아닌 입력에서는 글자 비교로 되돌아간다.
 *
 * **짝짓기는 백엔드에 물어본다** (`GET /api/presentations/{id}/source-map`). 예전에는 화면이
 * 같은 규칙을 옮겨 적었는데, 규칙이 한쪽만 자라면서 실제 파일과 다른 짝을 보여주게 됐다 —
 * 원본 2장에 얹힌 슬라이드를 원본 1장(표지) 옆에 놓는 식이다. 표지를 후보에서 빼는 것도,
 * 짝을 못 찾은 슬라이드를 남은 원본에 채우는 것도 export 만 알고 있던 규칙이었다.
 *
 * **순서는 원본 순서다.** 왼쪽이 원본이므로 "원본 1장부터 차례로 무엇이 됐나"로 읽는 것이
 * 자연스럽고, 청중별로 다시 짠 순서는 각 장의 "발표용 N번째" 표시에서 드러난다.
 *
 * 업로드가 PPTX 가 아니면(PDF·TXT) 얹을 원본이 없어 백엔드에도 짝이 없다. 그때만 화면이
 * 근거(`source_refs`)로 짝을 지어 글끼리 견준다 — 파일과 어긋날 대상 자체가 없다.
 *
 * 글자 비교의 원본 글은 chunk 가 아니라 `DocumentResponse.pages` 에서 온다. chunk 는 쪽 경계를
 * 넘어 묶이고 page 필드는 chunk 가 "시작한" 쪽이라, chunk 로 그리면 없는 장이 생기고 남의 글이 섞인다.
 *
 * X 로 닫으면 뒤의 결과 화면이 그대로 남아 있다.
 */
type Row =
  // number 는 발표용 덱에서 몇 번째 장인가 — 결과 슬라이드 이미지를 부르는 주소에 쓴다.
  | { kind: "rewritten"; page: number; original: string; slide: Slide; number: number }
  // 표지. 발표용 덱의 장이 아니라 원본 그대로 완성본 맨 앞에 남는 장이라 number 가 없다.
  | { kind: "kept"; page: number; original: string }
  | { kind: "added"; slide: Slide; number: number }
  | { kind: "cut"; slide: Slide; number: number }
  | { kind: "dropped"; page: number; original: string };

const KIND_LABELS: Record<Row["kind"], string> = {
  rewritten: "다시 씀",
  kept: "그대로",
  added: "새로 구성",
  cut: "파일에서 빠짐",
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
  const isPptx = result.document.filename.toLowerCase().endsWith(".pptx");
  const unitLabel = (page: number) => (isPptx ? `원본 슬라이드 ${page}` : `원문 ${page}쪽`);

  // 원본 슬라이드 이미지는 업로드가 PPTX 였을 때만 만들 수 있다. PDF·TXT 는 글자 비교뿐이다.
  const [showText, setShowText] = useState(false);
  const [showMarks, setShowMarks] = useState(true);
  const [active, setActive] = useState(0);
  const imageMode = isPptx && !showText;

  // 실제로 어느 원본에 얹혔는지. 규칙을 화면에 옮겨 적지 않고 백엔드가 정한 배치를 받는다.
  const [map, setMap] = useState<SourceMap | null>(null);
  useEffect(() => {
    let cancelled = false;
    fetchSourceMap(result.presentation_id).then((found) => {
      if (!cancelled) setMap(found);
    });
    return () => {
      cancelled = true;
    };
  }, [result.presentation_id]);

  const rows = useMemo(() => {
    // 왼쪽에 그릴 원본 글. 파싱한 쪽 그대로라 "원본 슬라이드 N" 이 실제 N 장과 같다.
    const byPage = new Map<number, string>();
    for (const page of pages) byPage.set(page.page, page.text);

    const deck = result.slide_deck.slides;
    const used = new Set<number>();
    const paired: Extract<Row, { page: number }>[] = [];
    // 원본에 짝이 없는 장은 뒤에 모은다 — 앞쪽은 원본 순서로 읽혀야 한다.
    const tail: Row[] = [];

    if (map && map.source_slides > 0) {
      if (map.cover_page !== null) {
        // 표지는 글까지 원본 그대로 파일 맨 앞에 남는다 (export_pptx._build_on_template).
        used.add(map.cover_page);
        paired.push({
          kind: "kept",
          page: map.cover_page,
          original: byPage.get(map.cover_page) ?? "",
        });
      }
      for (const pair of map.pairs) {
        const slide = deck[pair.number - 1];
        if (!slide) continue;
        if (pair.page !== null) {
          used.add(pair.page);
          paired.push({
            kind: "rewritten",
            page: pair.page,
            original: byPage.get(pair.page) ?? "",
            slide,
            number: pair.number,
          });
        } else {
          // output 이 없으면 원본 장수가 모자라 파일에서 빠진 장이다.
          tail.push({ kind: pair.output === null ? "cut" : "added", slide, number: pair.number });
        }
      }
    } else {
      // PPTX 가 아니거나 짝짓기를 받지 못했다. 글 대 글로만 견주므로 근거로 짝을 짓는다.
      const pageOf = new Map<string, number>();
      for (const item of result.source_analysis.source_evidence) pageOf.set(item.id, item.page);

      deck.forEach((slide, index) => {
        const counts = new Map<number, number>();
        for (const ref of slide.source_refs) {
          const page = pageOf.get(ref);
          if (page !== undefined) counts.set(page, (counts.get(page) ?? 0) + 1);
        }
        const page = [...counts.entries()]
          .sort((a, b) => b[1] - a[1])
          .find(([candidate]) => !used.has(candidate) && byPage.has(candidate))?.[0];

        const number = index + 1;
        if (page === undefined) {
          tail.push({ kind: "added", slide, number });
          return;
        }
        used.add(page);
        paired.push({ kind: "rewritten", page, original: byPage.get(page) ?? "", slide, number });
      });
    }

    // 짝이 없는 원본도 빠짐없이 보여준다. 실제 PPTX 에서 빠지는 장이 여기서 드러난다.
    for (const page of pages) {
      if (!used.has(page.page)) {
        paired.push({ kind: "dropped", page: page.page, original: page.text });
      }
    }

    // 원본 순서로 읽는다. 청중별로 다시 짠 순서는 각 장의 "발표용 N번째" 표시가 알려 준다.
    paired.sort((a, b) => a.page - b.page);
    return [...paired, ...tail];
  }, [result, pages, map]);

  const row = rows[Math.min(active, rows.length - 1)];

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
      // 입력란에 있을 때 화살표를 가로채지 않는다.
      if (event.target instanceof HTMLElement && event.target.closest("input, textarea")) return;
      if (event.key === "ArrowLeft") setActive((index) => Math.max(0, index - 1));
      if (event.key === "ArrowRight") setActive((index) => Math.min(rows.length - 1, index + 1));
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, rows.length]);

  // 변경 표시는 보고 있는 한 쌍만 가져온다. 열 때마다 전 장을 대조하면 첫 화면이 느려진다.
  const [regions, setRegions] = useState<DiffRegion[]>([]);
  useEffect(() => {
    setRegions([]);
    if (!imageMode || row?.kind !== "rewritten") return;

    let cancelled = false;
    fetchSlideDiff(result.presentation_id, row.number, row.page).then((found) => {
      if (!cancelled) setRegions(found);
    });
    return () => {
      cancelled = true;
    };
  }, [imageMode, result.presentation_id, row]);

  const marks = showMarks ? regions : [];
  const tally = (kind: Row["kind"]) => rows.filter((item) => item.kind === kind).length;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="원본과 결과 비교"
      className="animate-in fixed inset-0 z-50 flex flex-col bg-background/95 backdrop-blur-md"
    >
      <div className="glass shrink-0 border-b border-line px-4 py-3 sm:px-6">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-base font-bold tracking-tight sm:text-lg">원본과 결과 비교</h2>
            <p className="mt-0.5 truncate text-[11px] text-muted">
              {result.document.filename} · 원본 {pages.length}
              {isPptx ? "장" : "쪽"} → 발표용 {result.slide_deck.slides.length}장
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="hidden gap-1.5 text-[11px] text-muted lg:flex">
              {(Object.keys(KIND_LABELS) as Row["kind"][])
                .filter((kind) => tally(kind) > 0)
                .map((kind) => (
                  <Chip key={kind}>
                    {KIND_LABELS[kind]} {tally(kind)}
                  </Chip>
                ))}
            </span>
            {imageMode ? (
              <button
                type="button"
                onClick={() => setShowMarks((value) => !value)}
                aria-pressed={showMarks}
                className={`rounded-xl px-3 py-1.5 text-[11px] font-semibold ${
                  showMarks
                    ? "border border-[#e0483d]/50 bg-[#e0483d]/15 text-[#ff8078]"
                    : "btn-ghost"
                }`}
              >
                변경 표시 {showMarks ? "켜짐" : "꺼짐"}
              </button>
            ) : null}
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

      {/* 장 이동 탭. 어떤 장이 다시 쓰였고 어떤 장이 빠졌는지가 여기서 한눈에 읽힌다. */}
      <div
        role="tablist"
        aria-label="슬라이드 목록"
        className="shrink-0 overflow-x-auto border-b border-line px-4 py-2 sm:px-6"
      >
        <div className="mx-auto flex max-w-[1600px] gap-1.5">
          {rows.map((item, index) => (
            <button
              key={index}
              type="button"
              role="tab"
              aria-selected={index === active}
              onClick={() => setActive(index)}
              className={`flex shrink-0 items-baseline gap-2 rounded-xl border px-3 py-1.5 text-[11px] whitespace-nowrap transition-colors ${
                index === active
                  ? "border-accent/60 bg-accent-soft text-foreground"
                  : "border-line text-muted hover:border-accent/30"
              }`}
            >
              {/* 원본 순서로 늘어놓았으므로 앞의 번호는 원본 장 번호다. */}
              <span className="font-mono tabular-nums opacity-70">
                {"page" in item ? String(item.page).padStart(2, "0") : "--"}
              </span>
              <span className="max-w-[10rem] truncate font-semibold">{rowTitle(item)}</span>
              <span className="opacity-70">{KIND_LABELS[item.kind]}</span>
              {/* 청중에 맞춰 이야기 순서가 바뀐 것이 여기서 드러난다. */}
              {"number" in item ? (
                <span className="font-mono tabular-nums opacity-50">발표용 {item.number}</span>
              ) : null}
            </button>
          ))}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4 sm:px-6">
        <div className="mx-auto flex max-w-[1600px] flex-col gap-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <Side
              label={"page" in row ? unitLabel(row.page) : "원본에 짝이 없음"}
              kind={row.kind}
              muted
            >
              {!("page" in row) ? (
                <Placeholder>원문 전체에서 근거를 모아 새로 만든 슬라이드입니다.</Placeholder>
              ) : imageMode ? (
                <SlideImage
                  src={documentSlideUrl(result.document.document_id, row.page)}
                  alt={`원본 ${row.page}번째 슬라이드`}
                  regions={row.kind === "rewritten" ? marks : []}
                  fallback={<OriginalText text={row.original} />}
                />
              ) : (
                <OriginalText text={row.original} />
              )}
            </Side>

            <Side
              label={
                row.kind === "dropped"
                  ? "발표자료에 없음"
                  : row.kind === "cut"
                    ? "파일에 자리가 없음"
                    : row.kind === "kept"
                      ? "완성본 맨 앞 (원본 그대로)"
                      : `발표용 슬라이드 ${row.number}번째`
              }
              kind={row.kind}
            >
              {row.kind === "dropped" ? (
                <Placeholder>
                  이 원본은 발표 시간과 청중에 맞추는 과정에서 빠졌습니다. 내려받는 PPTX 에도
                  들어가지 않습니다.
                </Placeholder>
              ) : row.kind === "cut" ? (
                <Placeholder>
                  원본 슬라이드 장수가 모자라 내려받는 PPTX 에는 들어가지 않습니다. 이 장의 내용은
                  발표자료 탭과 Markdown·JSON 다운로드에 있습니다.
                </Placeholder>
              ) : row.kind === "kept" ? (
                // 표지는 글까지 원본 그대로 파일 맨 앞에 남는다 — 원본 그림을 그대로 보여준다.
                imageMode ? (
                  <SlideImage
                    src={documentSlideUrl(result.document.document_id, row.page)}
                    alt="완성본 맨 앞 슬라이드 (원본 표지 그대로)"
                    regions={[]}
                    fallback={<OriginalText text={row.original} />}
                  />
                ) : (
                  <OriginalText text={row.original} />
                )
              ) : imageMode ? (
                <SlideImage
                  src={presentationSlideUrl(result.presentation_id, row.number)}
                  alt={`발표용 ${row.number}번째 슬라이드`}
                  regions={marks}
                  fallback={<SlideText slide={row.slide} />}
                />
              ) : (
                <SlideText slide={row.slide} />
              )}
            </Side>
          </div>

          <ChangeList row={row} regions={regions} imageMode={imageMode} shown={showMarks} />

          <div className="flex items-center justify-between gap-3 pb-2">
            <button
              type="button"
              onClick={() => setActive((index) => Math.max(0, index - 1))}
              disabled={active === 0}
              className="btn-ghost rounded-xl px-4 py-2 text-xs font-semibold disabled:opacity-40"
            >
              ← 이전 장
            </button>
            <p className="text-[11px] text-muted">
              {active + 1} / {rows.length} · 좌우 화살표로 넘길 수 있습니다
            </p>
            <button
              type="button"
              onClick={() => setActive((index) => Math.min(rows.length - 1, index + 1))}
              disabled={active === rows.length - 1}
              className="btn-ghost rounded-xl px-4 py-2 text-xs font-semibold disabled:opacity-40"
            >
              다음 장 →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function rowTitle(row: Row): string {
  if (row.kind === "dropped") return `원본 ${row.page}장`;
  if (row.kind === "kept") return "표지";
  return row.slide.title || "제목 없음";
}

/**
 * 무엇이 어디서 달라졌는지를 글로도 남긴다.
 *
 * 네모만으로는 색으로만 상태를 알리는 꼴이 된다(docs/07). 번호가 이미지 위 네모의 번호와
 * 같아서, 목록을 읽으면 어느 자리 얘기인지 바로 찾아진다.
 */
function ChangeList({
  row,
  regions,
  imageMode,
  shown,
}: {
  row: Row;
  regions: DiffRegion[];
  imageMode: boolean;
  shown: boolean;
}) {
  if (row.kind !== "rewritten" || !imageMode) return null;

  return (
    <div className="rounded-2xl border border-line bg-surface-muted/40 px-4 py-3">
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
        달라진 자리 {regions.length}곳
      </p>
      {regions.length === 0 ? (
        <p className="mt-2 text-xs leading-relaxed text-muted">
          두 슬라이드를 대조하는 중이거나, 눈에 띄는 차이를 찾지 못했습니다.
        </p>
      ) : (
        <>
          <ul className="mt-2 flex flex-wrap gap-2">
            {regions.map((region, index) => (
              <li
                key={index}
                className="flex items-center gap-2 rounded-lg border border-[#e0483d]/40 bg-[#e0483d]/10 px-2.5 py-1 text-xs"
              >
                <span className="font-mono text-[10px] tabular-nums text-[#ff8078]">
                  {index + 1}
                </span>
                {region.label}
              </li>
            ))}
          </ul>
          <p className="mt-2.5 text-[11px] leading-relaxed text-muted">
            {shown
              ? "빨간 네모는 두 슬라이드를 실제로 렌더링해 픽셀로 대조한 자리입니다. 네모 밖은 원본 그대로 — 이미지·표·배경은 건드리지 않습니다."
              : "변경 표시가 꺼져 있습니다. 위의 ‘변경 표시’ 를 켜면 이미지 위에 자리를 그립니다."}
          </p>
        </>
      )}
    </div>
  );
}

/**
 * 백엔드가 구운 슬라이드 PNG 한 장. 실패하면 조용히 글자 비교로 되돌아간다.
 *
 * PowerPoint 가 없는 PC 에서는 503 이 온다 — 렌더링이 없다고 화면이 비면 안 된다.
 * next/image 를 쓰지 않는 이유: 주소가 백엔드 오리진이라 remotePatterns 설정이 필요하고,
 * 원본을 그대로 보여주는 것이 목적이라 최적화·리사이즈가 오히려 방해된다.
 *
 * 변경 표시 네모는 0~1 비율이고 PNG 가 16:9 라 aspect-video 칸에 그대로 맞는다.
 */
function SlideImage({
  src,
  alt,
  regions,
  fallback,
}: {
  src: string;
  alt: string;
  regions: DiffRegion[];
  fallback: React.ReactNode;
}) {
  const [state, setState] = useState<"loading" | "ready" | "failed">("loading");
  // 장을 넘기면 src 만 바뀌고 컴포넌트는 재사용된다. 그대로 두면 새 그림이 오는 동안
  // 이전 장의 그림이 "ready" 상태로 남아, 왼쪽은 새 장인데 오른쪽은 이전 장인 순간이 생긴다.
  const [shown, setShown] = useState(src);
  if (shown !== src) {
    setShown(src);
    setState("loading");
  }

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
        onLoad={() => setState("ready")}
        onError={() => setState("failed")}
        className={`h-full w-full object-contain transition-opacity duration-200 ${
          state === "ready" ? "opacity-100" : "opacity-0"
        }`}
      />
      {state === "ready"
        ? regions.map((region, index) => (
            // 같은 내용이 아래 목록에 글로 있다. 스크린 리더에는 두 번 읽히지 않게 한다.
            <div
              key={index}
              aria-hidden
              style={{
                left: `${region.x * 100}%`,
                top: `${region.y * 100}%`,
                width: `${region.w * 100}%`,
                height: `${region.h * 100}%`,
              }}
              className="pointer-events-none absolute rounded-[3px] border-2 border-[#e0483d] bg-[#e0483d]/10"
            >
              <span className="absolute -top-px -left-px rounded-br-[3px] bg-[#e0483d] px-1 font-mono text-[9px] leading-[14px] font-bold text-white tabular-nums">
                {index + 1}
              </span>
            </div>
          ))
        : null}
    </div>
  );
}

function Placeholder({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex aspect-video items-center justify-center rounded-xl border border-dashed border-line px-6">
      <p className="max-w-sm text-center text-xs leading-relaxed text-muted">{children}</p>
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
  return <p className="whitespace-pre-wrap text-sm leading-relaxed text-muted">{text}</p>;
}

function SlideText({ slide }: { slide: Slide }) {
  return (
    <>
      <h3 className="text-base font-bold leading-snug">{slide.title}</h3>
      {slide.takeaway ? (
        <p className="mt-2 border-l-2 border-accent bg-accent-soft px-3 py-2 text-sm leading-relaxed">
          {slide.takeaway}
        </p>
      ) : null}
      <ul className="mt-2 space-y-1.5">
        {slide.bullets.map((bullet) => (
          <li key={bullet} className="flex gap-2 text-sm leading-relaxed">
            <span aria-hidden className="mt-2 h-1 w-1 shrink-0 rounded-full bg-accent" />
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
    <div className={`rounded-2xl border border-line p-4 ${muted ? "bg-surface-muted/30" : ""}`}>
      <div className="mb-2.5 flex flex-wrap items-center gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
          {label}
        </span>
        {/* 상태는 색만이 아니라 글자로도 읽혀야 한다. */}
        <span
          className={`rounded-md border px-1.5 py-0.5 text-[10px] font-semibold ${
            kind === "dropped" || kind === "cut"
              ? "border-warn/40 bg-warn-soft text-warn"
              : kind === "added"
                ? "border-ok/40 bg-ok-soft text-ok"
                : kind === "kept"
                  ? "border-line bg-surface-muted text-muted"
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
