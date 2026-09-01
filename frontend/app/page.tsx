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

type Stage = "upload" | "conditions" | "generating" | "result";

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
    <main className="mx-auto w-full max-w-3xl px-4 py-10">
      <header className="mb-8">
        <p className="text-xs font-semibold tracking-widest text-accent">AUDIENCEDECK AI</p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight">
          청중이 이해할 때까지 리허설하는 발표 준비 도구
        </h1>
        <p className="mt-2 text-sm text-muted">
          기술문서 하나를 청중과 발표 조건에 맞춰 재구성하고, 발표 스크립트·예상 Q&amp;A와 함께
          원문 근거를 벗어나지 않았는지 검증합니다.
        </p>
      </header>

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
          verifying={verifying}
          onRestart={() => setStage("conditions")}
        />
      ) : null}
    </main>
  );
}
