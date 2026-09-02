/** 첫 그림 전에 DOM 을 고치는 인라인 스크립트. 서버 HTML 에서만 실행된다.
 *
 * 클라이언트에서는 `type="text/plain"` 으로 그려 브라우저가 무시하게 한다. React 가 그린
 * `<script>` 는 클라이언트에서 어차피 실행되지 않는데, 그대로 두면 개발 중 콘솔 경고
 * ("Encountered a script tag while rendering React component") 가 뜬다.
 * `type` 이 서버와 달라지므로 `suppressHydrationWarning` 이 함께 필요하다.
 *
 * 출처: node_modules/next/dist/docs/01-app/02-guides/preventing-flash-before-hydration.md
 */
export function InlineScript({ html }: { html: string }) {
  return (
    <script
      type={typeof window === "undefined" ? "text/javascript" : "text/plain"}
      suppressHydrationWarning
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
