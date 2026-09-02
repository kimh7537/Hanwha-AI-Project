"use client";

import { useCallback, useState } from "react";

import { ApiError, generatePresentation, uploadDocument, verifyPresentation } from "@/lib/api";
import type {
  DocumentResponse,
  GenerateResponse,
  PresentationRequest,
  VerificationReport,
} from "@/lib/types";
import { ConditionStep } from "@/components/ConditionStep";
import { GeneratingStep } from "@/components/GeneratingStep";
import { ResultView } from "@/components/ResultView";
import { UploadStep } from "@/components/UploadStep";
import { Kicker, Stepper } from "@/components/ui";

type Stage = "upload" | "conditions" | "generating" | "result";

const STAGE_STEPS = ["문서 업로드", "발표 조건", "AI 재설계", "결과 확인"];
const STAGE_INDEX: Record<Stage, number> = {
  upload: 0,
  conditions: 1,
  generating: 2,
  result: 3,
};

const DEFAULT_REQUEST: PresentationRequest = {
  audience: "customer",
  purpose: "technical_explanation",
  duration_minutes: 5,
  keywords: [],
  style: "persuasive",
  preserve_original_terms: true,
  slide_count: null,
};

function toMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "알 수 없는 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.";
}

export default function Page() {
  const [stage, setStage] = useState<Stage>("upload");
  const [document, setDocument] = useState<DocumentResponse | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const [request, setRequest] = useState<PresentationRequest>(DEFAULT_REQUEST);
  const [keywordText, setKeywordText] = useState("정확도, 도입 효과");

  const [progressIndex, setProgressIndex] = useState(0);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [report, setReport] = useState<VerificationReport | null>(null);
  const [verifying, setVerifying] = useState(false);

  async function handleUpload(file: File) {
    setUploading(true);
    setUploadError(null);
    try {
      setDocument(await uploadDocument(file));
    } catch (error) {
      setDocument(null);
      setUploadError(toMessage(error));
    } finally {
      setUploading(false);
    }
  }

  const runPipeline = useCallback(async () => {
    if (!document) return;

    const payload: PresentationRequest = {
      ...request,
      keywords: keywordText
        .split(",")
        .map((keyword) => keyword.trim())
        .filter(Boolean),
    };

    setStage("generating");
    setGenerateError(null);
    setResult(null);
    setReport(null);

    // 진행 표시는 실제 호출 단계를 따른다.
    // generate 호출이 모듈 A~D(0~3단계), verify 호출이 검증(4단계)에 해당한다.
    setProgressIndex(0);
    const ticker = window.setInterval(() => {
      setProgressIndex((index) => (index < 3 ? index + 1 : index));
    }, 400);

    try {
      const generated = await generatePresentation(document.document.document_id, payload);
      window.clearInterval(ticker);
      setResult(generated);
      setRequest(payload);

      setProgressIndex(4);
      setVerifying(true);
      const verified = await verifyPresentation(generated.presentation_id);
      setReport(verified);
      setProgressIndex(5);
      setStage("result");
    } catch (error) {
      window.clearInterval(ticker);
      setGenerateError(toMessage(error));
    } finally {
      setVerifying(false);
    }
  }, [document, keywordText, request]);

  return (
    <main className="mx-auto w-full max-w-5xl px-4 pb-16 pt-10">
      {/* 히어로는 첫 화면에서만 크게 편다. 이후 단계에서는 스텝퍼가 그 자리를 대신한다. */}
      {stage === "upload" ? (
        <header className="animate-in mb-10 text-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-line bg-surface-glass px-3.5 py-1.5 text-[11px] font-medium text-muted">
            <span aria-hidden className="pulse-ring h-1.5 w-1.5 rounded-full bg-accent" />
            Audience-Adaptive Presentation Designer
          </span>
          <h1 className="gradient-text mx-auto mt-5 max-w-3xl text-3xl font-black leading-[1.25] tracking-tight sm:text-[2.7rem]">
            같은 원문에서, 청중에 따라
            <br />
            발표를 다시 설계합니다
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-sm leading-relaxed text-muted sm:text-base">
            문장만 쉽게 바꾸지 않습니다.{" "}
            <strong className="font-semibold text-foreground">
              무엇을 넣고 뺄지, 몇 장으로 나눌지, 어떤 순서로 둘지
            </strong>
            를 청중에 맞춰 다시 구성하고, 발표 스크립트·예상 Q&amp;A와 함께 모든 문장이 원문을
            벗어나지 않았는지 검증합니다.
          </p>

          <div className="mt-8 grid gap-3 text-left sm:grid-cols-3">
            {[
              {
                k: "01",
                t: "청중별 재설계",
                d: "신입·실무자·임원·고객에 따라 슬라이드 장수와 순서까지 바뀝니다",
              },
              {
                k: "02",
                t: "AI 구성 전략",
                d: "왜 이 순서, 이 분량으로 만들었는지 AI가 근거를 설명합니다",
              },
              {
                k: "03",
                t: "원문 대비 검증",
                d: "모든 수치와 주장을 원문 문장까지 되짚어 확인합니다",
              },
            ].map((item, index) => (
              <div
                key={item.k}
                style={{ animationDelay: `${0.08 * index + 0.1}s` }}
                className="glass animate-in lift rounded-2xl border border-line p-4"
              >
                <Kicker>{item.k}</Kicker>
                <p className="mt-2 text-sm font-semibold">{item.t}</p>
                <p className="mt-1 text-xs leading-relaxed text-muted">{item.d}</p>
              </div>
            ))}
          </div>
        </header>
      ) : null}

      <div className="mx-auto mb-8 max-w-2xl">
        <Stepper steps={STAGE_STEPS} current={STAGE_INDEX[stage]} />
      </div>

      {stage === "upload" ? (
        <UploadStep
          document={document}
          uploading={uploading}
          error={uploadError}
          onUpload={handleUpload}
          onNext={() => setStage("conditions")}
        />
      ) : null}

      {stage === "conditions" ? (
        <ConditionStep
          request={request}
          keywordText={keywordText}
          onChange={setRequest}
          onKeywordTextChange={setKeywordText}
          onBack={() => setStage("upload")}
          onSubmit={runPipeline}
        />
      ) : null}

      {stage === "generating" ? (
        <GeneratingStep
          activeIndex={progressIndex}
          error={generateError}
          onRetry={runPipeline}
          onBack={() => {
            setGenerateError(null);
            setStage("conditions");
          }}
        />
      ) : null}

      {stage === "result" && result ? (
        <ResultView
          result={result}
          report={report}
          pages={document?.pages ?? []}
          verifying={verifying}
          onRestart={() => setStage("conditions")}
        />
      ) : null}
    </main>
  );
}
