import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { InlineScript } from "@/components/InlineScript";
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

/** 브라우저 기본 위젯(스크롤바·select·date)은 CSS 의 `color-scheme` 토큰이 테마별로 맞춘다.
 * 여기에 `colorScheme` 을 박아 두면 라이트로 바꿔도 위젯만 다크로 남는다. */
export const viewport: Viewport = { themeColor: "#0a0c11" };

/** 저장해 둔 테마를 첫 그림 전에 입힌다. 이게 없으면 라이트 사용자가 다크 한 번 깜빡임을 본다. */
const APPLY_THEME = `try{if(localStorage.getItem("theme")==="light"){document.documentElement.dataset.theme="light";var m=document.querySelector('meta[name="theme-color"]');if(m)m.content="#f5f6fa"}}catch(e){}`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // 서버는 늘 다크로 그리고 위 스크립트가 첫 그림 전에 라이트로 바꾼다. 그래서 하이드레이션
    // 시점의 DOM 은 서버 HTML 과 다를 수밖에 없다 — `suppressHydrationWarning` 은 그 차이를
    // 오류로 보지 말고 DOM 을 그대로 두라는 뜻이다. 없으면 React 가 트리를 다시 그리며
    // 스크립트가 넣은 값이 날아간다.
    <html
      lang="ko"
      data-theme="dark"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <head>
        <InlineScript html={APPLY_THEME} />
      </head>
      {/* 머리말·꼬리말은 `app/audiencedeck/layout.tsx` 로 내려갔다. `/` 의 사내 포털은
          제 상단바를 직접 그리므로 여기서 껍데기를 씌우면 두 겹이 된다. */}
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  );
}
