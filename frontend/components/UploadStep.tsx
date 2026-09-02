"use client";

import { useRef, useState } from "react";

import type { DocumentResponse } from "@/lib/types";
import { Card, ErrorNotice } from "./ui";

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

  return (
    <div className="space-y-4">
      <Card className="p-6">
        <h2 className="text-base font-semibold">1. 기술문서 업로드</h2>
        <p className="mt-1 text-sm text-muted">
          PDF, PPTX, TXT 파일을 올려 주세요. 업로드한 문서만을 근거로 발표자료를 만듭니다.
          PPTX는 슬라이드의 본문·표와 발표자 노트까지 읽습니다.
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
          className={`mt-5 rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors ${
            dragging ? "border-accent bg-accent-soft" : "border-line bg-surface-muted"
          }`}
        >
          <p className="text-sm text-muted">파일을 여기로 끌어다 놓거나</p>
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            className="mt-3 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {uploading ? "업로드 중…" : "파일 선택"}
          </button>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.pptx,.txt,.md"
            className="hidden"
            onChange={(event) => handleFiles(event.target.files)}
          />
        </div>

        {error ? (
          <div className="mt-4">
            <ErrorNotice message={error} />
          </div>
        ) : null}

        {document ? (
          <div className="mt-5 rounded-md border border-line bg-surface-muted p-4">
            <p className="text-sm font-medium">{document.document.filename}</p>
            <p className="mt-1 text-xs text-muted">
              {document.document.page_count}
              {document.document.filename.toLowerCase().endsWith(".pptx") ? "슬라이드" : "페이지"} ·{" "}
              {document.document.char_count.toLocaleString()}자
              · 근거 단위 {document.document.chunk_count}개로 분해했습니다
            </p>
          </div>
        ) : null}
      </Card>

      <div className="flex justify-end">
        <button
          type="button"
          onClick={onNext}
          disabled={!document}
          className="rounded-md border border-line bg-surface px-4 py-2 text-sm font-semibold transition-colors hover:bg-surface-muted disabled:opacity-40"
        >
          발표 조건 설정 →
        </button>
      </div>
    </div>
  );
}
