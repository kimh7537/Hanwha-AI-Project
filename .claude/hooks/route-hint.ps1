# UserPromptSubmit 훅 - 요청 내용을 보고 담당 문서와 서브에이전트를 자동으로 알려준다.
# 원본 기획안이 길기 때문에, 매번 전체를 읽지 않고 필요한 조각만 읽게 하는 것이 목적이다.

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$raw = [Console]::In.ReadToEnd()
if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }

try { $data = $raw | ConvertFrom-Json } catch { exit 0 }

$prompt = $data.prompt
if ([string]::IsNullOrWhiteSpace($prompt)) { exit 0 }

$routes = @(
    @{ Pattern = '파싱|PDF|chunk|청크|근거 추출|SourceAnalysis|문서 분석|PyMuPDF'
       Hint    = 'docs/02-document-analysis.md · doc-analyzer 서브에이전트' }
    @{ Pattern = '청중|신입|실무자|임원|고객|톤|용어 풀이|원어|AudienceContent'
       Hint    = 'docs/03-audience-transform.md · audience-transformer 서브에이전트' }
    @{ Pattern = '슬라이드|덱|장수|발표 시간|SlideDeck|PPTX|pptx'
       Hint    = 'docs/04-slide-planner.md · slide-planner 서브에이전트' }
    @{ Pattern = '스크립트|대본|예상 질문|Q&A|QA|리허설'
       Hint    = 'docs/05-presentation-support.md · presentation-support 서브에이전트' }
    @{ Pattern = '검증|근거 대조|숫자 오류|왜곡|누락|민감|Verification'
       Hint    = 'docs/06-verification.md · verifier 서브에이전트' }
    @{ Pattern = 'UI|화면|위저드|탭|프론트|Next|타입|API 연결|라우터|통합'
       Hint    = 'docs/07-frontend-ux.md, docs/08-api-and-env.md · frontend-integrator 서브에이전트' }
    @{ Pattern = '계약|스키마|contracts|types\.ts|필드'
       Hint    = 'docs/01-contracts.md · contract-sync 스킬을 먼저 실행' }
    @{ Pattern = '데모|시연|완료 조건|평가표|일정'
       Hint    = 'docs/09-schedule-and-demo.md · demo-check 스킬' }
)

$hits = New-Object System.Collections.Generic.List[string]
foreach ($route in $routes) {
    if ($prompt -match $route.Pattern) { $hits.Add($route.Hint) }
}

if ($hits.Count -eq 0) { exit 0 }

$message = "[기획안 라우팅] 이 요청과 관련된 명세와 담당자:`n - " + ($hits -join "`n - ") +
           "`n원본 claude-code-implementation-brief.md 전체를 읽지 말고 위 문서만 읽으세요. " +
           "여러 모듈에 걸친 요청이면 spec-route 스킬로 분해해 위임하세요."

$out = @{
    hookSpecificOutput = @{
        hookEventName     = 'UserPromptSubmit'
        additionalContext = $message
    }
}
$out | ConvertTo-Json -Depth 5 -Compress

exit 0
