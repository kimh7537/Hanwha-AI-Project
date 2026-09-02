"use client";

import { useEffect, useState } from "react";

/** 로딩 화면이 얼마나 지났는지 센다.
 *
 * 외부 LLM 호출이라 남은 시간을 알 방법이 없다. 경과 시간만은 사실이므로 그것을 화면에 두고,
 * 진행률·단계·안내 문구를 전부 이 값에서 파생시킨다. 200ms 마다 갱신해 숫자가 살아 움직인다.
 */
export function useElapsed(running: boolean): number {
  const [ms, setMs] = useState(0);

  useEffect(() => {
    if (!running) return;
    const start = Date.now();
    setMs(0);
    const id = window.setInterval(() => setMs(Date.now() - start), 200);
    return () => window.clearInterval(id);
  }, [running]);

  return running ? ms : 0;
}

/** 끝을 모르는 작업의 진행률 (0~95).
 *
 * 남은 시간을 모르므로 100% 를 먼저 그릴 수 없다. 대신 처음엔 빠르게, 뒤로 갈수록 느리게
 * 95% 에 다가가게 한다. 어느 순간에도 막대가 멈춰 있지 않아 "죽은 화면"으로 보이지 않으면서
 * 곧 끝난다고 거짓말도 하지 않는다. `floor` 는 실제로 확인된 진행도(완료된 단계)다.
 */
export function creepPercent(ms: number, floor = 0): number {
  const creep = 95 * (1 - Math.exp(-ms / 14000));
  return Math.round(Math.max(creep, floor));
}

/** `12초` 처럼 읽히는 경과 시간. 1분을 넘기면 분까지 적는다. */
export function formatElapsed(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}초`;
  return `${Math.floor(seconds / 60)}분 ${seconds % 60}초`;
}

/**
 * 기다리는 동안 읽을 것. 전부 이 제품이 실제로 하는 일이라 대기 시간이 설명 시간이 된다.
 * 지어낸 수치나 진행 상황은 적지 않는다 — 화면이 근거 없는 숫자를 말하면 안 된다.
 */
export const LOADING_TIPS = [
  "청중이 바뀌면 문장만이 아니라 무엇을 넣고 뺄지, 몇 장으로 나눌지가 함께 바뀝니다.",
  "모든 수치와 주장에 원문 쪽수가 붙습니다. 근거 배지를 누르면 원문 문장이 열립니다.",
  "원문에서 근거를 못 찾은 문장은 지우지 않고 정확성 검증 탭에 남겨 둡니다.",
  "고객용 자료에서는 내부 정보로 보이는 표현을 따로 짚어 드립니다.",
  "발표 스크립트와 예상 Q&A, 원문 대비 검증 리포트가 함께 만들어집니다.",
  "내려받는 PPTX 는 원본 위에 글만 갈아 끼워 이미지·표·글꼴이 그대로 남습니다.",
  "AI 응답이 실패해도 규칙 기반으로 이어받아 결과는 끝까지 나옵니다.",
] as const;

/** 경과 시간에서 안내 문구를 고른다. 따로 상태를 들 필요가 없다. */
export function tipAt(ms: number, tips: readonly string[] = LOADING_TIPS): string {
  return tips[Math.floor(ms / 5000) % tips.length];
}
