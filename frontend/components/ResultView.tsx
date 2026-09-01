"use client";

import { useMemo, useState } from "react";

import type { GenerateResponse, VerificationReport } from "@/lib/types";
import {
  AUDIENCE_LABELS,
  ISSUE_TYPE_LABELS,
  PURPOSE_LABELS,
  STATUS_DESCRIPTIONS,
  STATUS_LABELS,
  STYLE_LABELS,
} from "@/lib/labels";
import { ApiError, fetchPresentationPptx } from "@/lib/api";
import { download, downloadBlob, toMarkdown } from "@/lib/export";
import { EvidenceDialog, EvidenceRefs } from "./EvidenceRef";
import { Card, PublicReviewBadge, SectionTitle, SeverityBadge, StatusBadge } from "./ui";

const TABS = ["발표자료", "발표 스크립트", "예상 Q&A", "정확성 검증"] as const;
type Tab = (typeof TABS)[number];

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
      <Card className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">{result.slide_deck.title}</h2>
            <p className="mt-1 text-sm text-muted">
              {AUDIENCE_LABELS[result.request.audience]} ·{" "}
              {PURPOSE_LABELS[result.request.purpose]} · {result.request.duration_minutes}분 ·{" "}
              {STYLE_LABELS[result.request.style]} · 슬라이드 {result.slide_deck.slides.length}장
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {isCustomer ? <PublicReviewBadge /> : null}
            {activeReport ? <StatusBadge status={activeReport.status} /> : null}
          </div>
        </div>

        {result.meta.fallback_used ? (
          <p className="mt-3 rounded-md border border-warn/30 bg-warn-soft px-3 py-2 text-xs text-warn">
            AI 응답에 실패해 기본 분석 결과로 대체했습니다. ({result.meta.fallback_reason})
          </p>
        ) : null}

        {cautions.length > 0 ? (
          <ul className="mt-3 space-y-1.5 rounded-md border border-accent/30 bg-accent-soft p-3">
            {cautions.map((caution) => (
              <li key={caution} className="text-xs text-accent">
                · {caution}
              </li>
            ))}
          </ul>
        ) : null}

        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={downloadPptx}
            disabled={pptxWorking}
            aria-busy={pptxWorking}
            className="rounded-md border border-accent bg-accent-soft px-3 py-1.5 text-xs font-semibold text-accent hover:bg-accent-soft/70 disabled:opacity-60"
          >
            {pptxWorking ? "PPTX 만드는 중…" : "PPTX 다운로드"}
          </button>
          <button
            type="button"
            onClick={() =>
              download(
                `${result.slide_deck.title}.md`,
                toMarkdown(result),
                "text/markdown",
              )
            }
            className="rounded-md border border-line px-3 py-1.5 text-xs hover:bg-surface-muted"
          >
            Markdown 다운로드
          </button>
          <button
            type="button"
            onClick={() =>
              download(
                `${result.slide_deck.title}.json`,
                JSON.stringify(result, null, 2),
                "application/json",
              )
            }
            className="rounded-md border border-line px-3 py-1.5 text-xs hover:bg-surface-muted"
          >
            JSON 다운로드
          </button>
          <button
            type="button"
            onClick={onRestart}
            className="rounded-md border border-line px-3 py-1.5 text-xs hover:bg-surface-muted"
          >
            다른 조건으로 다시 만들기
          </button>
        </div>

        {pptxError ? (
          <p role="alert" className="mt-2 text-xs text-danger">
            {pptxError}
          </p>
        ) : null}

        <p className="mt-2 text-xs text-muted">
          PPTX 에는 발표자 노트로 스크립트가, 부록에 예상 Q&amp;A 와 검증 결과가 함께 들어갑니다.
          {result.document.filename.toLowerCase().endsWith(".pptx")
            ? " 업로드한 원본 PPTX 의 이미지·표·서식 위에 내용을 얹습니다. 발표 시간에 맞추느라 짝이 없는 원본 슬라이드는 빠집니다."
            : null}
        </p>
      </Card>

      <div role="tablist" className="flex flex-wrap gap-1 border-b border-line">
        {TABS.map((name) => (
          <button
            key={name}
            role="tab"
            aria-selected={tab === name}
            onClick={() => setTab(name)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm transition-colors ${
              tab === name
                ? "border-accent font-semibold text-accent"
                : "border-transparent text-muted hover:text-foreground"
            }`}
          >
            {name}
          </button>
        ))}
      </div>

      {tab === "발표자료" ? (
        <SlidesPanel result={result} onSelectEvidence={setEvidenceId} />
      ) : null}
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

function SlidesPanel({
  result,
  onSelectEvidence,
}: {
  result: GenerateResponse;
  onSelectEvidence: (id: string) => void;
}) {
  return (
    <div className="space-y-3">
      {result.slide_deck.slides.map((slide, index) => (
        <Card key={slide.id} className="p-5">
          <div className="flex items-baseline gap-3">
            <span className="font-mono text-xs text-muted">
              {String(index + 1).padStart(2, "0")}
            </span>
            <h3 className="text-base font-semibold">{slide.title}</h3>
          </div>

          <p className="mt-3 border-l-2 border-accent pl-3 text-sm font-medium">
            {slide.takeaway}
          </p>

          <ul className="mt-3 space-y-1.5">
            {slide.bullets.map((bullet) => (
              <li key={bullet} className="flex gap-2 text-sm leading-relaxed">
                <span aria-hidden className="text-muted">
                  ·
                </span>
                <span>{bullet}</span>
              </li>
            ))}
          </ul>

          <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-line pt-3">
            <p className="text-xs text-muted">추천 시각자료: {slide.visual_suggestion}</p>
            <EvidenceRefs refs={slide.source_refs} onSelect={onSelectEvidence} />
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
      <Card className="p-4">
        <p className="text-sm">
          예상 발표 시간 <strong>{Math.round(total / 6) / 10}분</strong>
          <span className="text-muted"> (목표 {result.request.duration_minutes}분)</span>
        </p>
        <p className="mt-1 text-xs text-muted">
          한국어 발화 속도를 초당 5자로 잡아 계산한 추정치입니다.
        </p>
      </Card>

      {result.presentation_support.scripts.map((script) => (
        <Card key={script.slide_id} className="p-5">
          <div className="flex items-baseline justify-between gap-3">
            <h3 className="text-sm font-semibold">{titleOf(script.slide_id)}</h3>
            <span className="text-xs text-muted">약 {script.duration_seconds}초</span>
          </div>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed">{script.script}</p>
          <p className="mt-3 rounded-md bg-surface-muted px-3 py-2 text-xs">
            <span className="font-semibold">꼭 말할 것</span> {script.must_say}
          </p>
        </Card>
      ))}
      <p className="text-xs text-muted">
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
    <div className="space-y-4">
      <div className="space-y-3">
        <SectionTitle hint={`${AUDIENCE_LABELS[result.request.audience]}이 자주 묻는 질문입니다.`}>
          예상 질문 {qa.length}개
        </SectionTitle>
        {qa.map((item) => {
          const unverified = item.answer.startsWith("원문 확인 필요");
          return (
            <Card key={item.question} className="p-5">
              <p className="text-sm font-semibold">Q. {item.question}</p>
              <p
                className={`mt-2 text-sm leading-relaxed ${
                  unverified ? "text-warn" : ""
                }`}
              >
                {item.answer}
              </p>
              <div className="mt-3 border-t border-line pt-3">
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
          {rehearsal_cards.map((card) => (
            <Card key={card.question} className="p-4">
              <p className="text-sm font-medium">{card.question}</p>
              <p className="mt-1 text-xs text-muted">{card.why}</p>
              <p className="mt-2 text-xs">
                보강할 슬라이드: <span className="font-mono">{card.recommended_slide}</span>
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
      <Card className="p-6">
        <p className="text-sm text-muted">원문과 대조하는 중입니다…</p>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      <Card className="p-5">
        <div className="flex flex-wrap items-center gap-3">
          <StatusBadge status={report.status} />
          <span className="text-xs text-muted">{STATUS_DESCRIPTIONS[report.status]}</span>
        </div>
        <p className="mt-3 text-sm">{report.summary}</p>
        <p className="mt-2 text-xs text-muted">
          슬라이드 {report.checked_slides}장을 원문 근거와 대조했습니다. 근거·숫자 검사는 규칙
          로직으로 수행하므로 같은 입력에는 항상 같은 결과가 나옵니다.
        </p>
      </Card>

      {report.items.length === 0 ? (
        <Card className="p-5">
          <p className="text-sm">원문과 어긋나는 내용을 찾지 못했습니다.</p>
        </Card>
      ) : (
        report.items.map((item, index) => (
          <Card key={`${item.type}-${item.slide_id}-${index}`} className="p-5">
            <div className="flex flex-wrap items-center gap-2">
              <SeverityBadge severity={item.severity} />
              <span className="text-xs font-medium">{ISSUE_TYPE_LABELS[item.type]}</span>
              {item.slide_id ? (
                <span className="font-mono text-xs text-muted">{item.slide_id}</span>
              ) : null}
            </div>
            <p className="mt-2 text-sm leading-relaxed">{item.message}</p>
            <p className="mt-2 rounded-md bg-surface-muted px-3 py-2 text-xs">
              <span className="font-semibold">수정 제안</span> {item.suggested_fix}
            </p>
            {item.source_refs.length > 0 ? (
              <div className="mt-3">
                <EvidenceRefs refs={item.source_refs} onSelect={onSelectEvidence} />
              </div>
            ) : null}
          </Card>
        ))
      )}

      {unverified.length > 0 ? (
        <Card className="p-5">
          <SectionTitle hint="원문에서 근거를 찾지 못해 발표자료에 넣지 않은 항목입니다.">
            원문 확인 필요 {unverified.length}건
          </SectionTitle>
          <ul className="space-y-1">
            {unverified.map((item) => (
              <li key={item} className="text-xs text-muted">
                · {item}
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      <p className="text-xs text-muted">
        이 검증은 확인이 필요한 지점을 알려 줄 뿐 사람 검토를 대체하지 않습니다. 최종 책임은
        발표자에게 있습니다.
      </p>
    </div>
  );
}
