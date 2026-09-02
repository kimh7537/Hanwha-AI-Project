import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 개발 서버가 좌측 하단에 띄우는 Next.js 표시등을 끈다. 시연을 `next dev` 로 하는데
  // 화면 구석에 프레임워크 로고가 떠 있으면 만든 화면이 아닌 것이 같이 찍힌다.
  // 컴파일·런타임 오류는 이 설정과 무관하게 그대로 보인다.
  devIndicators: false,
};

export default nextConfig;
