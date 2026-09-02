# PostToolUse(Write|Edit) 훅 - 공통 데이터 계약이 한쪽만 수정되는 것을 감지한다.
# docs/01-contracts.md 의 "4곳 동시 수정" 규칙을 상기시킨다.

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$raw = [Console]::In.ReadToEnd()
if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }

try { $data = $raw | ConvertFrom-Json } catch { exit 0 }

$filePath = $data.tool_input.file_path
if (-not $filePath) { exit 0 }

$path = $filePath -replace '\\', '/'
$notes = New-Object System.Collections.Generic.List[string]

if ($path -match 'backend/app/models/contracts\.py$') {
    $notes.Add('Pydantic 계약을 수정했습니다. frontend/lib/types.ts, backend/fixtures/*.json, docs/01-contracts.md 를 함께 갱신해야 합니다.')
}
if ($path -match 'frontend/lib/types\.ts$') {
    $notes.Add('TypeScript 계약을 수정했습니다. backend/app/models/contracts.py, backend/fixtures/*.json, docs/01-contracts.md 를 함께 갱신해야 합니다.')
}
if ($path -match 'backend/fixtures/.*\.json$') {
    $notes.Add('fixture 를 수정했습니다. 계약 스키마와 일치하는지 확인하세요.')
}
if ($path -match 'docs/01-contracts\.md$') {
    $notes.Add('계약 문서를 수정했습니다. Pydantic / TypeScript / fixture 를 문서에 맞추세요.')
}
if ($path -match 'claude-code-implementation-brief\.md$') {
    $notes.Add('원본 기획안을 수정했습니다. docs/ 아래 분해 문서에도 같은 변경을 반영해야 서브에이전트가 옛 명세로 작업하지 않습니다.')
}

if ($notes.Count -eq 0) { exit 0 }

$message = ($notes -join ' ') + ' 동기화 절차는 contract-sync 스킬을 사용하세요.'

$out = @{
    hookSpecificOutput = @{
        hookEventName     = 'PostToolUse'
        additionalContext = $message
    }
}
$out | ConvertTo-Json -Depth 5 -Compress

exit 0
