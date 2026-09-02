# SessionStart 훅 - 세션 시작 시 프로젝트 현재 상태와 라우팅 맵을 주입한다.
# 긴 기획안을 다시 읽지 않아도 어디서부터 이어가야 할지 알 수 있게 한다.

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$null = [Console]::In.ReadToEnd()

$root = Get-Location

function Test-Item([string]$relative) {
    return (Test-Path (Join-Path $root $relative))
}

$state = New-Object System.Collections.Generic.List[string]

$checks = [ordered]@{
    'backend/app/models/contracts.py'   = '공통 계약(Pydantic)'
    'frontend/lib/types.ts'             = '공통 계약(TypeScript)'
    'backend/fixtures/sample_document.txt' = '샘플 기술문서'
    'backend/app/services/analyzer.py'  = '모듈 A 문서 분석'
    'backend/app/services/audience.py'  = '모듈 B 청중 변환'
    'backend/app/services/planner.py'   = '모듈 C 슬라이드 구성'
    'backend/app/services/support.py'   = '모듈 D 발표 지원'
    'backend/app/services/verifier.py'  = '모듈 E 검증'
    'backend/app/services/pipeline.py'  = '파이프라인 오케스트레이션'
    'frontend/app/page.tsx'             = '위저드 UI'
}

foreach ($key in $checks.Keys) {
    $mark = if (Test-Item $key) { '완료' } else { '미구현' }
    $state.Add("$mark  $($checks[$key])  ($key)")
}

$message = @"
[AudienceDeck AI 세션 브리핑]

원본 기획안(claude-code-implementation-brief.md)은 길므로 전체를 읽지 마세요.
docs/ 아래 모듈별 문서로 분해되어 있고, 각 모듈에는 전용 서브에이전트가 있습니다.

공통 전제: docs/00-overview.md (프로젝트 정의·파이프라인), docs/01-contracts.md (데이터 계약)
모듈별: 02 문서분석 / 03 청중변환 / 04 슬라이드 / 05 발표지원 / 06 검증 / 07 UI / 08 API·환경변수 / 09 일정·데모 / 10 품질·안전

서브에이전트: doc-analyzer, audience-transformer, slide-planner, presentation-support, verifier, frontend-integrator
스킬: spec-route(작업 분해·위임), contract-sync(계약 4곳 동기화), evidence-audit(근거 무결성), demo-check(데모 기준 7항목)

현재 구현 상태:
$($state -join "`n")

넓은 요청을 받으면 먼저 spec-route 스킬로 분해하세요.
"@

$out = @{
    hookSpecificOutput = @{
        hookEventName     = 'SessionStart'
        additionalContext = $message
    }
}
$out | ConvertTo-Json -Depth 5 -Compress

exit 0
