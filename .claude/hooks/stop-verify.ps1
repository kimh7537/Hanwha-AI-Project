# Stop 훅 - 작업을 마칠 때 계약 동기화 상태를 조용히 점검한다.
# 문제가 없으면 아무것도 출력하지 않는다(정지를 막지 않는 자문용 훅).

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$null = [Console]::In.ReadToEnd()

$root = Get-Location
$python = Join-Path $root 'backend\.venv\Scripts\python.exe'
$checker = Join-Path $root '.claude\skills\contract-sync\check_contracts.py'

if (-not (Test-Path $python)) { exit 0 }
if (-not (Test-Path $checker)) { exit 0 }

$output = & $python $checker
$code = $LASTEXITCODE

if ($code -eq 0) { exit 0 }

Write-Output "[계약 점검] 데이터 계약 불일치가 남아 있습니다:"
Write-Output ($output -join "`n")
Write-Output "contract-sync 스킬로 Pydantic / TypeScript / fixture / docs 를 함께 맞추세요."

exit 0
