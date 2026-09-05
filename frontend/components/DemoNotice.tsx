"use client";

import { useEffect, useRef, useState } from "react";

import { fetchHealth } from "@/lib/api";

/**
 * 한 번 닫은 자리는 이 세션 동안 다시 뜨지 않는다.
 *
 * 자리마다 따로 세는 이유: 결과 화면과 슬라이드 비교는 들어가는 문이 다르고, 비교는 결과에서
 * 한참 지나 열린다. 하나로 세면 결과 화면에서 닫은 사람이 비교 화면에서는 사정을 못 본 채
 * 원본과 생성물을 나란히 놓게 된다 — 문장 품질이 가장 눈에 띄는 자리가 거기다.
 *
 * `useState` 만으로 두면 컴포넌트가 다시 붙을 때마다 되살아난다. 닫았는데 또 막아서는
 * 알림은 안내가 아니라 방해다. 새로고침하면 초기화되는 것은 의도한 것이다 — 심사자가
 * 새로 들어오면 사정을 한 번은 봐야 한다.
 */
const dismissed = new Set<string>();

/**
 * Claude API 를 끊어 둔 배포에 붙는 고지.
 *
 * 제출용 배포는 비용 때문에 외부 API 없이 돈다. 그때 결과는 LLM 이 쓴 문장이 아니라
 * 휴리스틱이 원문에서 고른 문장이라 눈에 띄게 투박하다. 아무 말 없이 내놓으면 심사자가
 * 그것을 "완성도가 낮다"로 읽으므로, 화면이 먼저 사정을 밝힌다.
 *
 * **구석의 쪽지가 아니라 화면 한가운데다.** 한때 우하단에 작게 띄웠는데, 결과가 처음 뜨는
 * 순간 눈은 슬라이드로 가지 구석으로 가지 않는다. 못 읽고 지나친 고지는 없는 것과 같다.
 * 뒤를 어둡게 덮고 흐려서 읽을 것이 이것 하나뿐이게 만든 다음, 닫고 나면 길을 비켜준다.
 *
 * **켜고 끄는 스위치를 따로 두지 않는다.** `/api/health` 의 `llm_enabled` 가 곧 그 상태다.
 * 배포에서 키를 빼는 순간 저절로 뜨고 다시 꽂으면 저절로 사라진다 — 제출 직전에 사람이
 * 잊어버릴 자리를 만들지 않는다. 개발 중 로컬은 mock provider 라 늘 뜨는데 그게 맞다.
 *
 * 두 겹인 이유: 겉의 두 줄은 심사자가 아닌 사람도 읽을 말이라 두루뭉술하고, 접힌 안쪽은
 * 채점자에게 필요한 정확한 사정이다. 처음부터 "API 를 막아 뒀다"를 펼쳐 두면 화면이
 * 변명문으로 시작한다.
 */
export function DemoNotice({
  /** 이 알림이 뜨는 자리. 자리마다 한 번씩 뜬다. */
  scope,
}: {
  scope: "result" | "compare";
}) {
  const [limited, setLimited] = useState(false);
  const [closed, setClosed] = useState(() => dismissed.has(scope));
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    let alive = true;
    void fetchHealth().then((health) => {
      // health 가 null 이면 백엔드에 못 닿은 것이다. 그건 다른 오류이고 화면이 따로 알린다.
      if (alive && health) setLimited(!health.llm_enabled);
    });
    return () => {
      alive = false;
    };
  }, []);

  const open = limited && !closed;

  useEffect(() => {
    if (!open) return;

    // 뜨자마자 닫기 버튼에 초점을 준다. 화면을 막아 놓고 Tab 을 여러 번 눌러야 빠져나갈 수
    // 있으면 키보드로 쓰는 사람에게는 막다른 길이다.
    closeRef.current?.focus();

    function onKey(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      // **capture 단계**로 잡아 전파를 끊는다. 비교 화면도 window 에서 Escape 로 오버레이를
      // 닫는데, 그냥 두면 Escape 한 번에 알림과 비교 화면이 함께 닫혀 원본 대조가 사라진다.
      event.stopPropagation();
      dismissed.add(scope);
      setClosed(true);
    }
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [open, scope]);

  if (!open) return null;

  const close = () => {
    dismissed.add(scope);
    setClosed(true);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="demo-notice-title"
      onClick={close}
      className="animate-in fixed inset-0 z-[60] grid place-items-center bg-black/55 px-4 backdrop-blur-sm"
    >
      {/* 안쪽 클릭이 배경까지 올라가면 글을 읽으려고 누른 순간 닫힌다. */}
      <div
        onClick={(event) => event.stopPropagation()}
        className="glass w-full max-w-md rounded-2xl border border-warn/40 p-5 text-warn shadow-[0_30px_80px_-30px_rgba(0,0,0,0.8)]"
      >
        <p id="demo-notice-title" className="text-sm font-bold tracking-tight">
          데모 버전 안내
        </p>
        <p className="mt-2 text-xs leading-relaxed">
          지금은 체험용으로 제한된 환경에서 동작하고 있어, 발표자료·스크립트·Q&amp;A 문장이 실제
          서비스만큼 다듬어지지 않습니다. 청중별 구성과 원문 대비 검증은 그대로 확인하실 수
          있습니다. 양해 부탁드립니다.
        </p>

        {/* 토글을 손으로 만들지 않는다. `details` 가 접힘 상태·키보드 조작·스크린리더 전달을
         * 이미 다 한다. 여기에 useState 를 하나 더 두면 그 셋을 직접 맞춰야 한다. */}
        <details className="group mt-3">
          <summary className="inline-flex cursor-pointer list-none items-center gap-1 rounded-lg border border-warn/30 px-2.5 py-1.5 text-[11px] font-semibold transition-colors duration-200 hover:bg-warn/15">
            <span aria-hidden className="transition-transform duration-200 group-open:rotate-90">
              ▸
            </span>
            자세한 사정 보기
          </summary>
          <p className="mt-2 border-l-2 border-warn/30 pl-3 text-[11px] leading-relaxed">
            현재 프로젝트는{" "}
            <strong className="font-semibold">
              비용 문제로 Claude 외부 API 연결을 막아 둔 상태
            </strong>
            입니다. 그래서 이 주소에서는 LLM 대신 내장 휴리스틱이 문장을 만듭니다. API 를 연결한
            상태의 실제 동작은 <strong className="font-semibold">함께 제출한 영상 파일</strong>을
            참조해 주시기 바랍니다. 평가 점수 측정에 참고 및 양해 부탁드립니다.
          </p>
        </details>

        <button
          ref={closeRef}
          type="button"
          onClick={close}
          className="mt-4 w-full rounded-xl border border-warn/40 bg-warn/15 px-4 py-2.5 text-xs font-semibold transition-colors duration-200 hover:bg-warn/25"
        >
          확인했습니다
        </button>
      </div>
    </div>
  );
}
