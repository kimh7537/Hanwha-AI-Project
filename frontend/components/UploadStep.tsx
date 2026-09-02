"use client";

import { useRef, useState } from "react";

import type { DocumentResponse } from "@/lib/types";
import { Button, Card, ErrorNotice, Kicker, Stat } from "./ui";

export function UploadStep({
  document,
  uploading,
  error,
  onUpload,
  onNext,
}: {
  document: DocumentResponse | null;
  uploading: boolean;
  error: string | null;
  onUpload: (file: File) => void;
  onNext: () => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function handleFiles(files: FileList | null) {
    const file = files?.[0];
    if (file) onUpload(file);
  }

  const isPptx = document?.document.filename.toLowerCase().endsWith(".pptx") ?? false;

  return (
    <div className="space-y-4">
      <Card className="p-6 sm:p-8">
        <Kicker>Step 01</Kicker>
        <h2 className="mt-2 text-xl font-bold tracking-tight">기술문서 업로드</h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
          PDF · PPTX · TXT 를 지원합니다. 업로드한 문서만을 근거로 발표자료를 만들고, PPTX 는
          슬라이드 본문·표와 발표자 노트까지 읽습니다.
        </p>

        <div
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            handleFiles(event.dataTransfer.files);
          }}
          className={`mt-6 rounded-2xl border-2 border-dashed px-6 py-12 text-center transition-all duration-300 ${
            dragging
              ? "scale-[1.01] border-accent bg-accent-soft"
              : "border-line bg-surface-muted/40 hover:border-line-strong"
          }`}
        >
          <span
            aria-hidden
            className={`mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-line bg-gradient-to-br from-accent/25 to-accent-2/10 text-2xl transition-transform duration-300 ${
              dragging ? "-translate-y-1 scale-110" : ""
            }`}
          >
            ↑
          </span>
          <p className="mt-4 text-sm font-medium">
            {dragging ? "여기에 놓으면 바로 분석합니다" : "파일을 여기로 끌어다 놓으세요"}
          </p>
          <p className="mt-1 text-xs text-muted">또는</p>
          <Button
            variant="primary"
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            aria-busy={uploading}
            className="mt-4"
          >
            {uploading ? (
              <>
                <Spinner />
                업로드 중…
              </>
            ) : (
              "파일 선택"
            )}
          </Button>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.pptx,.txt,.md"
            className="hidden"
            onChange={(event) => handleFiles(event.target.files)}
          />
          <p className="mt-4 text-[11px] text-muted">PDF · PPTX · TXT · MD</p>
        </div>

        {error ? (
          <div className="mt-5">
            <ErrorNotice message={error} />
          </div>
        ) : null}

        {document ? (
          <div className="animate-in mt-6 rounded-2xl border border-ok/25 bg-ok-soft/40 p-4">
            <div className="flex items-center gap-2.5">
              <span
                aria-hidden
                className="flex h-6 w-6 items-center justify-center rounded-full bg-ok/20 text-xs text-ok"
              >
                ✓
              </span>
              <p className="truncate text-sm font-semibold">{document.document.filename}</p>
            </div>
            <div className="mt-3 grid gap-2 sm:grid-cols-3">
              <Stat
                label={isPptx ? "슬라이드" : "페이지"}
                value={`${document.document.page_count}${isPptx ? "장" : "쪽"}`}
              />
              <Stat label="글자 수" value={`${document.document.char_count.toLocaleString()}자`} />
              <Stat label="근거 단위" value={`${document.document.chunk_count}개`} />
            </div>
            <p className="mt-2.5 text-[11px] leading-relaxed text-muted">
              발표자료의 모든 문장은 이 {document.document.chunk_count}개 근거 단위까지 되짚을 수
              있습니다.
            </p>
          </div>
        ) : null}
      </Card>

      <div className="flex justify-end">
        <Button variant="primary" onClick={onNext} disabled={!document}>
          발표 조건 설정 <span aria-hidden>→</span>
        </Button>
      </div>
    </div>
  );
}

/** 버튼 안에서만 쓰는 작은 스피너. */
function Spinner() {
  return (
    <span
      aria-hidden
      className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent"
    />
  );
}
