# PreToolUse(Write|Edit) 훅 - 실제 API 키가 저장소 파일에 기록되는 것을 차단한다.
# docs/10-quality-safety.md "비밀정보" 규칙을 기계적으로 강제한다.

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$raw = [Console]::In.ReadToEnd()
if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }

try { $data = $raw | ConvertFrom-Json } catch { exit 0 }

$filePath = $data.tool_input.file_path
if (-not $filePath) { exit 0 }

$content = ''
foreach ($field in @('content', 'new_string')) {
    $value = $data.tool_input.$field
    if ($value) { $content += "`n" + $value }
}
if ([string]::IsNullOrWhiteSpace($content)) { exit 0 }

$reasons = New-Object System.Collections.Generic.List[string]

# 1) 실제 자격증명 패턴
$patterns = @{
    'sk-ant-[A-Za-z0-9_\-]{24,}'  = 'Anthropic API 키'
    'sk-proj-[A-Za-z0-9_\-]{24,}' = 'OpenAI 프로젝트 키'
    'sk-[A-Za-z0-9]{32,}'         = 'OpenAI API 키'
    'AIza[0-9A-Za-z_\-]{30,}'     = 'Google API 키'
    'xox[baprs]-[A-Za-z0-9\-]{10,}' = 'Slack 토큰'
    'ghp_[A-Za-z0-9]{30,}'        = 'GitHub 토큰'
}
foreach ($pattern in $patterns.Keys) {
    if ($content -match $pattern) {
        $reasons.Add("$($patterns[$pattern]) 로 보이는 값이 포함되어 있습니다.")
    }
}

# 2) .env.example 에는 변수 이름만 (값 금지)
if ($filePath -match '\.env\.example$') {
    $secretVars = 'LLM_API_KEY|CHROMA_API_KEY|CHROMA_TENANT|CHROMA_DATABASE|OPENAI_API_KEY|ANTHROPIC_API_KEY'
    foreach ($line in ($content -split "`r?`n")) {
        if ($line -match "^\s*($secretVars)\s*=\s*(\S.*)$") {
            $reasons.Add(".env.example 의 $($Matches[1]) 에 값이 들어 있습니다. 변수 이름만 두세요.")
        }
    }
}

if ($reasons.Count -gt 0) {
    $message = "비밀정보 규칙 위반으로 차단했습니다 (docs/10-quality-safety.md):`n - " +
               ($reasons -join "`n - ") +
               "`n실제 값은 .env(gitignore 대상)에만 두고, 저장소 파일에는 변수 이름만 남기세요."
    $out = @{
        hookSpecificOutput = @{
            hookEventName            = 'PreToolUse'
            permissionDecision       = 'deny'
            permissionDecisionReason = $message
        }
    }
    $out | ConvertTo-Json -Depth 5 -Compress
}

exit 0
