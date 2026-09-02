import { ThemeToggle } from "@/components/ThemeToggle";

/** AudienceDeck 화면에만 붙는 머리말·꼬리말.
 *
 * 루트 레이아웃에 두면 `/` 의 사내 포털에도 얹혀서 포털 상단이 두 겹이 된다.
 * 두 화면이 한 앱 안에 살면서 각자의 껍데기를 유지하려면 이 자리가 맞다.
 */
export default function AudienceDeckLayout({ children }: LayoutProps<"/audiencedeck">) {
  return (
    <>
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
          <div className="flex items-center gap-2">
            <span className="hidden rounded-full border border-line bg-surface-glass px-3 py-1 text-[11px] text-muted sm:block">
              한화투자증권 · AI 업무 효율화 프로젝트
            </span>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <div className="flex-1">{children}</div>

      <footer className="border-t border-line px-4 py-6 text-center text-[11px] leading-relaxed text-muted">
        생성된 모든 문장은 업로드한 원문을 근거로 만들어지며, 발표 전 담당자 검토가 필요합니다.
      </footer>
    </>
  );
}
