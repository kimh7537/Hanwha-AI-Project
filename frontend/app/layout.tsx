import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AudienceDeck AI",
  description:
    "기술문서를 청중에 맞춰 재구성하고, 발표 스크립트·예상 Q&A·원문 대비 검증까지 제공하는 발표 지원 도구",
};

/** 브라우저 기본 위젯(스크롤바·select·date)까지 다크로 맞춘다. */
export const viewport: Viewport = { colorScheme: "dark", themeColor: "#0a0c11" };

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ko"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">
        <header className="sticky top-0 z-40 border-b border-line bg-background/70 backdrop-blur-xl">
          <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-4 py-3">
            <div className="flex items-center gap-2.5">
              <span
                aria-hidden
                className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-accent to-accent-2 text-[13px] font-black text-accent-ink shadow-[0_8px_24px_-10px_rgba(255,138,61,0.9)]"
              >
                AD
              </span>
              <span className="leading-tight">
                <span className="block text-sm font-bold tracking-tight">AudienceDeck AI</span>
                <span className="block text-[11px] text-muted">
                  같은 기술도, 듣는 사람이 다르면 발표는 달라야 합니다
                </span>
              </span>
            </div>
            <span className="hidden rounded-full border border-line bg-surface-glass px-3 py-1 text-[11px] text-muted sm:block">
              한화투자증권 · AI 업무 효율화 프로젝트
            </span>
          </div>
        </header>

        <div className="flex-1">{children}</div>

        <footer className="border-t border-line px-4 py-6 text-center text-[11px] leading-relaxed text-muted">
          생성된 모든 문장은 업로드한 원문을 근거로 만들어지며, 발표 전 담당자 검토가 필요합니다.
        </footer>
      </body>
    </html>
  );
}
