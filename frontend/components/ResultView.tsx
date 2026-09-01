"use client";

import { useMemo, useState } from "react";

import type { Audience, GenerateResponse, VerificationReport } from "@/lib/types";
import {
  AUDIENCE_LABELS,
  ISSUE_TYPE_LABELS,
  PURPOSE_LABELS,
  STATUS_DESCRIPTIONS,
  STATUS_LABELS,
  STYLE_LABELS,
} from "@/lib/labels";
import { ApiError, fetchPresentationPptx, generatePresentation } from "@/lib/api";
import { download, downloadBlob, toMarkdown } from "@/lib/export";
import { EvidenceDialog, EvidenceRefs } from "./EvidenceRef";
import {
  Button,
  Card,
  Kicker,
  PublicReviewBadge,
  SectionTitle,
  SeverityBadge,
  Stat,
  StatusBadge,
} from "./ui";

const TABS = ["발표자료", "청중 비교", "발표 스크립트", "예상 Q&A", "정확성 검증"] as const;
type Tab = (typeof TABS)[number];

const ALL_AUDIENCES: Audience[] = ["newcomer", "practitioner", "executive", "customer"];

export function ResultView({
  result,
  report,
  verifying,
  onRestart,
}: {
  result: GenerateResponse;
  report: VerificationReport | null;
  verifying: boolean;
  onRestart: () => void;
}) {
  const [tab, setTab] = useState<Tab>("발표자료");
  const [evidenceId, setEvidenceId] = useState<string | null>(null);
  const [pptxWorking, setPptxWorking] = useState(false);
  const [pptxError, setPptxError] = useState<string | null>(null);

  // PPTX 는 백엔드에서 만든다. 실패해도 Markdown / JSON 다운로드는 그대로 쓸 수 있다.
  async function downloadPptx() {
    setPptxWorking(true);
    setPptxError(null);
    try {
      const { blob, filename } = await fetchPresentationPptx(result.presentation_id);
      downloadBlob(filename, blob);
    } catch (error) {
      setPptxError(
        error instanceof ApiError
          ? error.message
          : "PPTX 파일을 만들지 못했습니다. Markdown 또는 JSON 다운로드를 이용해 주세요.",
      );
    } finally {
      setPptxWorking(false);
    }
  }

  const evidenceById = useMemo(
    () => new Map(result.source_analysis.source_evidence.map((item) => [item.id, item])),
    [result],
  );

  const isCustomer = result.request.audience === "customer";
  const cautions = result.audience_content.cautions;
  const activeReport = report ?? result.verification_report;

  return (
    <div className="space-y-4">
      <Card className="overflow-hidden">
        {/* 상단 그라디언트 띠 — 결과 화면이 "완성물"로 보이게 하는 최소 장치. */}
        <div aria-hidden className="h-1 bg-gradient-to-r from-accent via-accent-2 to-transparent" />
        <div className="p-6 sm:p-7">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <Kicker>Result</Kicker>
              <h2 className="mt-1.5 text-2xl font-bold leading-snug tracking-tight">
                {result.slide_deck.title}
              </h2>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {isCustomer ? <PublicReviewBadge /> : null}
              {activeReport ? <StatusBadge status={activeReport.status} /> : null}
            </div>
          </div>

          <div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-5">
            <Stat label="청중" value={AUDIENCE_LABELS[result.request.audience]} />
            <Stat label="목적" value={PURPOSE_LABELS[result.request.purpose]} />
            <Stat label="발표 시간" value={`${result.request.duration_minutes}분`} />
            <Stat label="스타일" value={STYLE_LABELS[result.request.style]} />
            <Stat label="슬라이드" value={`${result.slide_deck.slides.length}장`} />
          </div>

          {result.meta.fallback_used ? (
            <p className="mt-4 rounded-xl border border-warn/30 bg-warn-soft px-3.5 py-2.5 text-xs leading-relaxed text-warn">
              AI 응답에 실패해 기본 분석 결과로 대체했습니다. ({result.meta.fallback_reason})
            </p>
          ) : null}

          {cautions.length > 0 ? (
            <ul className="mt-4 space-y-1.5 rounded-xl border border-accent/25 bg-accent-soft p-3.5">
              {cautions.map((caution) => (
                <li key={caution} className="text-xs leading-relaxed text-accent">
                  · {caution}
                </li>
              ))}
            </ul>
          ) : null}

          <div className="mt-5 flex flex-wrap gap-2">
            <Button
              variant="primary"
              onClick={downloadPptx}
              disabled={pptxWorking}
              aria-busy={pptxWorking}
              className="px-4 py-2 text-xs"
            >
              {pptxWorking ? "PPTX 만드는 중…" : "PPTX 다운로드"}
            </Button>
            <Button
              className="px-4 py-2 text-xs"
              onClick={() =>
                download(`${result.slide_deck.title}.md`, toMarkdown(result), "text/markdown")
              }
            >
              Markdown
            </Button>
            <Button
              className="px-4 py-2 text-xs"
              onClick={() =>
                download(
                  `${result.slide_deck.title}.json`,
                  JSON.stringify(result, null, 2),
                  "application/json",
                )
              }
            >
              JSON
            </Button>
            <Button className="px-4 py-2 text-xs" onClick={onRestart}>
              다른 조건으로 다시 만들기
            </Button>
          </div>

          {pptxError ? (
            <p role="alert" className="mt-2 text-xs text-danger">
              {pptxError}
            </p>
          ) : null}

          <p className="mt-3 text-[11px] leading-relaxed text-muted">
            PPTX 에는 발표자 노트로 스크립트가, 부록에 예상 Q&amp;A 와 검증 결과가 함께 들어갑니다.
            {result.document.filename.toLowerCase().endsWith(".pptx")
              ? " 업로드한 원본 PPTX 의 이미지·표·서식 위에 내용을 얹습니다. 발표 시간에 맞추느라 짝이 없는 원본 슬라이드는 빠집니다."
              : null}
          </p>
        </div>
      </Card>

      <div
        role="tablist"
        className="glass sticky top-[57px] z-30 flex flex-wrap gap-1 rounded-2xl border border-line p-1.5"
      >
        {TABS.map((name) => (
          <button
            key={name}
            role="tab"
            aria-selected={tab === name}
            onClick={() => setTab(name)}
            className={`rounded-xl px-3.5 py-2 text-xs font-semibold transition-all duration-300 sm:text-sm ${
              tab === name
                ? "bg-gradient-to-br from-accent to-accent-2 text-accent-ink shadow-[0_10px_26px_-14px_rgba(255,138,61,0.95)]"
                : "text-muted hover:bg-surface-muted hover:text-foreground"
            }`}
          >
            {name}
          </button>
        ))}
      </div>

      {tab === "발표자료" ? (
        <SlidesPanel result={result} onSelectEvidence={setEvidenceId} />
      ) : null}
      {tab === "청중 비교" ? <ComparePanel result={result} /> : null}
      {tab === "발표 스크립트" ? <ScriptsPanel result={result} /> : null}
      {tab === "예상 Q&A" ? <QAPanel result={result} onSelectEvidence={setEvidenceId} /> : null}
      {tab === "정확성 검증" ? (
        <VerificationPanel
          report={activeReport}
          verifying={verifying}
          unverified={result.source_analysis.unverified}
          onSelectEvidence={setEvidenceId}
        />
      ) : null}

      <EvidenceDialog
        evidence={evidenceId ? (evidenceById.get(evidenceId) ?? null) : null}
        onClose={() => setEvidenceId(null)}
      />
    </div>
  );
}

/** 같은 원문·같은 조건에서 청중만 바꿔 다시 생성하고 좌우로 세운다.
 *
 * 새 엔드포인트를 만들지 않는다 — generate 를 audience 만 바꿔 한 번 더 부르면 된다.
 * 결과는 이 컴포넌트 안에만 두고 저장하지 않는다(비교는 보고 나면 끝나는 화면이다).
 */
function ComparePanel({ result }: { result: GenerateResponse }) {
  const current = result.request.audience;
  const [other, setOther] = useState<Audience | null>(null);
  const [compared, setCompared] = useState<GenerateResponse | null>(null);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(audience: Audience) {
    setWorking(true);
    setError(null);
    setOther(audience);
    setCompared(null);
    try {
      setCompared(
        await generatePresentation(result.document.document_id, {
          ...result.request,
          audience,
        }),
      );
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "비교할 발표자료를 만들지 못했습니다. 잠시 후 다시 시도해 주세요.",
      );
    } finally {
      setWorking(false);
    }
  }

  const mine = result.slide_deck.slides.length;
  const theirs = compared?.slide_deck.slides.length ?? 0;

  return (
    <div className="space-y-3">
      <Card className="p-6">
        <SectionTitle hint="원문과 목적·시간·키워드는 그대로 두고 청중만 바꿔 다시 설계합니다. 표현이 아니라 구성이 달라지는지 직접 확인하세요.">
          다른 청중이면 어떻게 달라지나
        </SectionTitle>
        <div className="mt-4 flex flex-wrap gap-2">
          {ALL_AUDIENCES.filter((audience) => audience !== current).map((audience) => (
            <button
              key={audience}
              type="button"
              onClick={() => run(audience)}
              disabled={working}
              aria-pressed={other === audience}
              className={`rounded-xl border px-4 py-2 text-xs font-semibold transition-all duration-300 disabled:opacity-50 ${
                other === audience
                  ? "border-accent bg-accent-soft text-accent"
                  : "border-line bg-surface-glass hover:-translate-y-0.5 hover:border-line-strong hover:bg-surface-muted"
              }`}
            >
              {/* "실무자과" 같은 조사 오류를 피하려고 받침 있는 "용"을 끼운다. */}
              {AUDIENCE_LABELS[audience]}용과 비교하기
            </button>
          ))}
        </div>

        {working ? (
          <div className="mt-5 space-y-2" aria-live="polite">
            <p className="text-xs text-muted">
              {other ? AUDIENCE_LABELS[other] : ""}용으로 다시 설계하는 중입니다…
            </p>
            <span aria-hidden className="shimmer block h-2 w-2/3 rounded-full" />
            <span aria-hidden className="shimmer block h-2 w-1/2 rounded-full" />
          </div>
        ) : null}

        {error ? (
          <p role="alert" className="mt-4 text-xs text-danger">
            {error}
          </p>
        ) : null}

        {compared ? (
          <p className="mt-5 rounded-xl border border-accent/25 bg-accent-soft px-4 py-3 text-sm">
            <span className="font-semibold text-accent">
              {AUDIENCE_LABELS[current]} {mine}장
            </span>
            <span aria-hidden className="mx-2 text-muted">
              →
            </span>
            <span className="font-semibold text-accent">
              {AUDIENCE_LABELS[compared.request.audience]} {theirs}장
            </span>
            <span className="ml-2 text-xs text-muted">
              {mine === theirs
                ? "장수는 같지만 순서와 담은 내용이 다릅니다"
                : `청중만 바꿨는데 ${Math.abs(mine - theirs)}장이 ${mine > theirs ? "줄었" : "늘었"}습니다`}
            </span>
          </p>
        ) : null}
      </Card>

      {compared ? (
        <div className="grid gap-3 md:grid-cols-2">
          <CompareColumn result={result} note="지금 보고 있는 자료" />
          <CompareColumn result={compared} note="청중만 바꾼 자료" highlight />
        </div>
      ) : null}
    </div>
  );
}

function CompareColumn({
  result,
  note,
  highlight = false,
}: {
  result: GenerateResponse;
  note: string;
  highlight?: boolean;
}) {
  return (
    <Card className={`p-6 ${highlight ? "border-accent/40" : ""}`}>
      <p className="text-[11px] uppercase tracking-[0.14em] text-muted">{note}</p>
      <div className="mt-1.5 flex items-baseline gap-2">
        <h3 className="text-lg font-bold tracking-tight">
          {AUDIENCE_LABELS[result.request.audience]}용
        </h3>
        <span className="rounded-full border border-line px-2 py-0.5 text-[11px] text-muted">
          {result.slide_deck.slides.length}장
        </span>
      </div>

      <p className="mt-4 rounded-xl border border-line bg-surface-muted/60 p-3.5 text-xs leading-relaxed">
        {result.slide_deck.strategy}
      </p>

      <ol className="mt-4 space-y-2.5">
        {result.slide_deck.slides.map((slide, index) => (
          <li
            key={slide.id}
            style={{ animationDelay: `${index * 0.04}s` }}
            className={`animate-in border-l-2 pl-3.5 ${
              highlight ? "border-accent/50" : "border-line"
            }`}
          >
            <p className="text-sm font-semibold">
              <span className="font-mono text-[11px] text-muted">
                {String(index + 1).padStart(2, "0")}
              </span>{" "}
              {slide.title}
            </p>
            <p className="mt-0.5 text-xs leading-relaxed text-muted">{slide.takeaway}</p>
          </li>
        ))}
      </ol>
    </Card>
  );
}

function SlidesPanel({
  result,
  onSelectEvidence,
}: {
  result: GenerateResponse;
  onSelectEvidence: (id: string) => void;
}) {
  return (
    <div className="space-y-3">
      {result.slide_deck.strategy ? (
        <Card className="border-accent/30 p-6">
          <div className="flex items-start gap-3">
            <span
              aria-hidden
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-accent to-accent-2 text-base text-accent-ink"
            >
              ✦
            </span>
            <div>
              <Kicker>AI 구성 전략</Kicker>
              <p className="mt-2 text-sm leading-relaxed">{result.slide_deck.strategy}</p>
              <p className="mt-2.5 text-xs leading-relaxed text-muted">
                같은 원문이라도 청중이 달라지면 무엇을 넣고 뺄지, 몇 장으로 나눌지가 함께 바뀝니다.
              </p>
            </div>
          </div>
        </Card>
      ) : null}

      {result.slide_deck.slides.map((slide, index) => (
        <Card key={slide.id} hover delay={index * 0.05} className="p-6">
          <div className="flex items-start gap-4">
            <span
              aria-hidden
              className="mt-0.5 font-mono text-2xl font-black leading-none text-line-strong"
            >
              {String(index + 1).padStart(2, "0")}
            </span>
            <div className="min-w-0 flex-1">
              <h3 className="text-lg font-bold tracking-tight">{slide.title}</h3>

              <p className="mt-3 rounded-r-lg border-l-2 border-accent bg-accent-soft/50 py-2 pl-3.5 text-sm font-medium leading-relaxed">
                {slide.takeaway}
              </p>

              <ul className="mt-4 space-y-2">
                {slide.bullets.map((bullet) => (
                  <li key={bullet} className="flex gap-2.5 text-sm leading-relaxed">
                    <span aria-hidden className="mt-2 h-1 w-1 shrink-0 rounded-full bg-accent" />
                    <span>{bullet}</span>
                  </li>
                ))}
              </ul>

              <div className="mt-5 flex flex-wrap items-center justify-between gap-2 border-t border-line pt-3.5">
                <p className="text-xs text-muted">추천 시각자료: {slide.visual_suggestion}</p>
                <EvidenceRefs refs={slide.source_refs} onSelect={onSelectEvidence} />
              </div>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}

function ScriptsPanel({ result }: { result: GenerateResponse }) {
  const total = result.presentation_support.scripts.reduce(
    (sum, script) => sum + script.duration_seconds,
    0,
  );
  const target = result.request.duration_minutes * 60;
  const titleOf = (slideId: string) =>
    result.slide_deck.slides.find((slide) => slide.id === slideId)?.title ?? slideId;

  return (
    <div className="space-y-3">
      <Card className="p-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <Kicker>예상 발표 시간</Kicker>
            <p className="mt-1.5 text-3xl font-black tabular-nums">
              {Math.round(total / 6) / 10}
              <span className="ml-1 text-base font-bold text-muted">분</span>
            </p>
          </div>
          <p className="text-xs text-muted">목표 {result.request.duration_minutes}분</p>
        </div>
        <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-surface-muted">
          <div
            className="h-full rounded-full bg-gradient-to-r from-accent to-accent-2"
            style={{ width: `${Math.min(100, Math.round((total / target) * 100))}%` }}
          />
        </div>
        <p className="mt-2.5 text-[11px] text-muted">
          한국어 발화 속도를 초당 5자로 잡아 계산한 추정치입니다.
        </p>
      </Card>

      {result.presentation_support.scripts.map((script, index) => (
        <Card key={script.slide_id} hover delay={index * 0.05} className="p-6">
          <div className="flex items-baseline justify-between gap-3">
            <h3 className="text-sm font-bold">{titleOf(script.slide_id)}</h3>
            <span className="shrink-0 rounded-full border border-line px-2 py-0.5 text-[11px] text-muted">
              약 {script.duration_seconds}초
            </span>
          </div>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-[1.8]">{script.script}</p>
          <p className="mt-4 rounded-xl border border-line bg-surface-muted/60 px-3.5 py-2.5 text-xs leading-relaxed">
            <span className="font-semibold text-accent">꼭 말할 것</span> {script.must_say}
          </p>
        </Card>
      ))}
      <p className="text-[11px] text-muted">
        목표 시간 {target}초 기준으로 슬라이드마다 분량을 배분했습니다.
      </p>
    </div>
  );
}

function QAPanel({
  result,
  onSelectEvidence,
}: {
  result: GenerateResponse;
  onSelectEvidence: (id: string) => void;
}) {
  const { qa, rehearsal_cards } = result.presentation_support;

  return (
    <div className="space-y-5">
      <div className="space-y-3">
        <SectionTitle hint={`${AUDIENCE_LABELS[result.request.audience]}이 자주 묻는 질문입니다.`}>
          예상 질문 {qa.length}개
        </SectionTitle>
        {qa.map((item, index) => {
          const unverified = item.answer.startsWith("원문 확인 필요");
          return (
            <Card key={item.question} hover delay={index * 0.05} className="p-6">
              <p className="flex gap-2.5 text-sm font-bold">
                <span aria-hidden className="text-accent">
                  Q
                </span>
                {item.question}
              </p>
              <p
                className={`mt-3 flex gap-2.5 text-sm leading-relaxed ${
                  unverified ? "text-warn" : ""
                }`}
              >
                <span aria-hidden className="font-bold text-muted">
                  A
                </span>
                <span>{item.answer}</span>
              </p>
              <div className="mt-4 border-t border-line pt-3.5">
                <EvidenceRefs refs={item.source_refs} onSelect={onSelectEvidence} />
              </div>
            </Card>
          );
        })}
      </div>

      {rehearsal_cards.length > 0 ? (
        <div className="space-y-3">
          <SectionTitle hint="AI 관객이 물어볼 질문과, 그에 대비해 보강할 슬라이드입니다.">
            리허설 카드
          </SectionTitle>
          {rehearsal_cards.map((card, index) => (
            <Card key={card.question} hover delay={index * 0.05} className="p-5">
              <p className="text-sm font-semibold">{card.question}</p>
              <p className="mt-1.5 text-xs leading-relaxed text-muted">{card.why}</p>
              <p className="mt-2.5 text-xs">
                보강할 슬라이드:{" "}
                <span className="font-mono text-accent">{card.recommended_slide}</span>
              </p>
            </Card>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function VerificationPanel({
  report,
  verifying,
  unverified,
  onSelectEvidence,
}: {
  report: VerificationReport | null;
  verifying: boolean;
  unverified: string[];
  onSelectEvidence: (id: string) => void;
}) {
  if (verifying || !report) {
    return (
      <Card className="space-y-3 p-6">
        <p className="text-sm text-muted">원문과 대조하는 중입니다…</p>
        <span aria-hidden className="shimmer block h-2.5 w-3/4 rounded-full" />
        <span aria-hidden className="shimmer block h-2.5 w-1/2 rounded-full" />
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      <Card className="p-6">
        <div className="flex flex-wrap items-center gap-3">
          <StatusBadge status={report.status} />
          <span className="text-xs text-muted">{STATUS_DESCRIPTIONS[report.status]}</span>
        </div>
        <p className="mt-4 text-sm leading-relaxed">{report.summary}</p>
        <p className="mt-2.5 text-[11px] leading-relaxed text-muted">
          슬라이드 {report.checked_slides}장을 원문 근거와 대조했습니다. 근거·숫자 검사는 규칙
          로직으로 수행하므로 같은 입력에는 항상 같은 결과가 나옵니다.
        </p>
      </Card>

      {report.items.length === 0 ? (
        <Card className="p-6">
          <p className="text-sm">원문과 어긋나는 내용을 찾지 못했습니다.</p>
        </Card>
      ) : (
        report.items.map((item, index) => (
          <Card
            key={`${item.type}-${item.slide_id}-${index}`}
            hover
            delay={index * 0.05}
            className="p-6"
          >
            <div className="flex flex-wrap items-center gap-2">
              <SeverityBadge severity={item.severity} />
              <span className="text-xs font-semibold">{ISSUE_TYPE_LABELS[item.type]}</span>
              {item.slide_id ? (
                <span className="font-mono text-[11px] text-muted">{item.slide_id}</span>
              ) : null}
            </div>
            <p className="mt-3 text-sm leading-relaxed">{item.message}</p>
            <p className="mt-3 rounded-xl border border-line bg-surface-muted/60 px-3.5 py-2.5 text-xs leading-relaxed">
              <span className="font-semibold text-accent">수정 제안</span> {item.suggested_fix}
            </p>
            {item.source_refs.length > 0 ? (
              <div className="mt-3.5">
                <EvidenceRefs refs={item.source_refs} onSelect={onSelectEvidence} />
              </div>
            ) : null}
          </Card>
        ))
      )}

      {unverified.length > 0 ? (
        <Card className="p-6">
          <SectionTitle hint="원문에서 근거를 찾지 못해 발표자료에 넣지 않은 항목입니다.">
            원문 확인 필요 {unverified.length}건
          </SectionTitle>
          <ul className="space-y-1.5">
            {unverified.map((item) => (
              <li key={item} className="text-xs leading-relaxed text-muted">
                · {item}
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      <p className="text-[11px] leading-relaxed text-muted">
        이 검증은 확인이 필요한 지점을 알려 줄 뿐 사람 검토를 대체하지 않습니다. 최종 책임은
        발표자에게 있습니다.
      </p>
    </div>
  );
}
