"use client";

import { useEffect, useState } from "react";

/** 다크/라이트 전환. 색은 전부 CSS 토큰에서 나오므로 여기서는 `<html data-theme>` 만 바꾼다.
 *
 * 첫 그림에서 깜빡이지 않도록 저장값 적용은 `app/layout.tsx` 의 인라인 스크립트가 먼저 한다.
 * 이 컴포넌트는 그 결과를 읽어 라벨을 맞춘다 (서버는 항상 다크로 그리므로 상태 초기값도 다크).
 */
export function ThemeToggle() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    setTheme(document.documentElement.dataset.theme === "light" ? "light" : "dark");
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
