"use client";

import { useLayoutEffect, useState } from "react";

/** 다크/라이트 전환. 색은 전부 CSS 토큰에서 나오므로 여기서는 `<html data-theme>` 만 바꾼다.
 *
 * 첫 그림에서 깜빡이지 않도록 저장값 적용은 `app/layout.tsx` 의 인라인 스크립트가 먼저 한다.
 * 이 컴포넌트는 라벨을 맞추고, 아래처럼 값을 다시 입힌다 (서버는 항상 다크로 그린다).
 */
export function ThemeToggle() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  // 개발 모드의 StrictMode 재마운트에서 React 는 `<html>` 의 속성을 JSX 가 관리하는 것만
  // 남기고 지운다 — 인라인 스크립트가 넣은 라이트가 그때 날아간다. 저장값에서 다시 입힌다.
  // 운영 빌드에서는 재마운트가 없어 아래는 사실상 no-op 다.
  // `useEffect` 가 아니라 `useLayoutEffect` 인 이유는 그림 전에 돌아야 깜빡이지 않아서다.
  useLayoutEffect(() => {
    let stored: string | null = null;
    try {
      stored = localStorage.getItem("theme");
    } catch {
      // 저장이 막힌 환경에서는 기본값(다크)으로 둔다.
    }
    const next = stored === "light" ? "light" : "dark";
    setTheme(next);
    document.documentElement.dataset.theme = next;
  }, []);

  function toggle() {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
    document.documentElement.dataset.theme = next;
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute("content", next === "light" ? "#f5f6fa" : "#0a0c11");
    try {
      localStorage.setItem("theme", next);
    } catch {
      // 시크릿 모드 등에서 저장이 막혀도 이번 세션 전환은 그대로 동작해야 한다.
    }
  }

  const nextLabel = theme === "light" ? "다크 모드" : "라이트 모드";

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={`${nextLabel}로 전환`}
      className="flex items-center gap-1.5 rounded-full border border-line bg-surface-glass px-3 py-1 text-[11px] text-muted transition-colors hover:border-line-strong hover:text-foreground"
    >
      <span aria-hidden>{theme === "light" ? "◐" : "◑"}</span>
      {nextLabel}
    </button>
  );
}
