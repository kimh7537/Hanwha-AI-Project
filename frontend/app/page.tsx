import Link from "next/link";

/** 사내 포털(Cleverse) 홈. AudienceDeck 은 여기서 `/audiencedeck` 로 들어간다.
 *
 * 포털에서 다른 포트의 앱으로 넘기면 배포할 때 도메인이 둘로 갈린다. 두 화면을
 * 한 앱의 두 라우트로 두면 주소만 바뀌고 화면 구성은 그대로다.
 */
const NAV_ITEMS = ["메일", "게시판", "전자결재", "사원찾기"];

const STORIES = [
  "한화, 지속가능한 미래를 위한 새로운 약속",
  "2026년 상반기 주요 경영 성과 안내",
  "임직원 여러분께 전하는 CEO 메시지",
];

export default function PortalPage() {
  return (
    <main className="min-h-screen bg-[#f6f6f6] text-[#232323]">
      <nav className="bg-[#161616] px-5 text-white sm:px-10">
        <div className="mx-auto flex h-[68px] max-w-[1480px] items-center gap-8">
          <Link href="/" className="flex shrink-0 items-center gap-3">
            <span className="clevers-mark" aria-hidden="true" />
            <span className="text-[20px] font-semibold tracking-[-0.04em]">Cleverse</span>
          </Link>
          <div className="h-6 w-px bg-white/20" />
          <div className="hidden items-center gap-8 text-[13px] text-white/70 lg:flex">
            {NAV_ITEMS.map((item) => (
              <button key={item} type="button" className="transition hover:text-white">
                {item}
              </button>
            ))}
          </div>
          {/* 포털 흉내인 위 항목들과 달리 이것만 실제로 동작하므로 좁은 화면에서도 접지 않는다.
              하단 "시작하기" 카드와 짝이고, 둘 다 `/audiencedeck` 으로 간다. */}
          <Link
            href="/audiencedeck"
            className="shrink-0 text-[13px] text-white/70 transition hover:text-white lg:-ml-2"
          >
            AudienceDeck AI
          </Link>
          <div className="ml-auto flex items-center gap-5 text-[13px] text-white/80">
            <button type="button" className="hidden transition hover:text-white sm:block">
              Ch.H+
            </button>
            <button type="button" aria-label="알림" className="text-lg transition hover:text-[#f47b32]">
              ♧
            </button>
            <button type="button" aria-label="전체 메뉴" className="grid grid-cols-3 gap-1 p-1">
              {Array.from({ length: 9 }).map((_, index) => (
                <span key={index} className="h-1.5 w-1.5 rounded-[1px] bg-white/80" />
              ))}
            </button>
          </div>
        </div>
      </nav>

      <div className="mx-auto max-w-[1480px] px-5 pb-20 sm:px-10">
        <section className="pt-10 sm:pt-14">
          <div className="flex items-end justify-between">
            <div>
              <p className="text-xs font-bold tracking-[0.18em] text-[#ed6a22]">CHANNEL H+</p>
              <h1 className="mt-2 text-3xl font-bold tracking-[-0.05em] sm:text-4xl">
                Channel H+ 주요소식
              </h1>
            </div>
            <button type="button" className="text-sm text-[#888] hover:text-[#ed6a22]">
              전체보기 →
            </button>
          </div>
          <div className="mt-7 grid gap-5 md:grid-cols-3">
            {STORIES.map((story, index) => (
              <article
                key={story}
                className="group overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-black/[0.04]"
              >
                <div
                  className={`h-36 ${index === 0 ? "bg-[#ed6a22]" : index === 1 ? "bg-[#252525]" : "bg-[#f0d1bb]"} p-6`}
                >
                  <span className="text-4xl font-bold text-white/90">0{index + 1}</span>
                  <p className="mt-10 text-xs font-medium text-white/75">CHANNEL H+ · 2026.09.02</p>
                </div>
                <div className="p-5">
                  <h2 className="text-[16px] font-semibold leading-6 group-hover:text-[#ed6a22]">
                    {story}
                  </h2>
                  <p className="mt-3 text-xs text-[#999]">새로운 소식을 확인해보세요</p>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="mt-12 grid gap-5 lg:grid-cols-2">
          <Board
            title="회사공지"
            items={[
              "2026년 추석 연휴 및 휴무일 안내",
              "사내 보안 정책 변경 안내",
              "임직원 건강검진 신청 일정",
            ]}
          />
          <Board
            title="그룹게시판"
            items={[
              "한화그룹 공통 복지 제도 안내",
              "계열사 우수 사례를 공유합니다",
              "이번 주 그룹 주요 일정",
            ]}
          />
        </section>

        <section className="mt-12 overflow-hidden rounded-2xl bg-[#211d1b] px-7 py-8 text-white sm:px-10">
          <div className="flex flex-col items-start justify-between gap-6 sm:flex-row sm:items-center">
            <div>
              <p className="text-xs font-bold tracking-[0.16em] text-[#f47b32]">NEW SERVICE</p>
              <h2 className="mt-2 text-2xl font-bold tracking-[-0.04em]">AI Project Assistant</h2>
              <p className="mt-2 text-sm text-white/60">문서에서 발표까지, 업무 준비를 더 간편하게</p>
            </div>
            <Link
              href="/audiencedeck"
              className="rounded-xl bg-[#ed6a22] px-6 py-3 text-sm font-bold transition hover:bg-[#ff8744]"
            >
              시작하기 <span aria-hidden="true">→</span>
            </Link>
          </div>
        </section>
      </div>
    </main>
  );
}

function Board({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-black/[0.04]">
      <div className="flex items-center justify-between border-b border-[#eee] pb-4">
        <h2 className="text-lg font-bold">{title}</h2>
        <button type="button" className="text-xs text-[#999] hover:text-[#ed6a22]">
          더보기 +
        </button>
      </div>
      <div className="divide-y divide-[#f1f1f1]">
        {items.map((item) => (
          <button
            type="button"
            key={item}
            className="flex w-full items-center justify-between py-4 text-left text-sm text-[#555] transition hover:text-[#ed6a22]"
          >
            <span className="truncate pr-4">{item}</span>
            <span className="shrink-0 text-xs text-[#aaa]">2026.09.02</span>
          </button>
        ))}
      </div>
    </section>
  );
}
