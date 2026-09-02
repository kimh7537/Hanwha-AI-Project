# PNG 를 터미널 안에 ANSI 색으로 그린다. 원격 터미널이라 이미지 뷰어를 못 쓸 때 쓴다.
#
#   .\show.ps1 07-원본과비교-슬라이드.png
#   .\show.ps1 07-원본과비교-슬라이드.png -Width 160
#
# 한 글자 칸에 위/아래 픽셀 두 개를 담는다(윗반칸 문자의 글자색=위, 배경색=아래).
# 24bit 색을 쓰므로 Windows Terminal 에서 보인다. 글자는 뭉개진다 — 배치를 보는 용도다.
param(
    [Parameter(Mandatory = $true)][string]$Path,
    [int]$Width = 100
)

Add-Type -AssemblyName System.Drawing

$full = (Resolve-Path -LiteralPath $Path).Path
$src = [System.Drawing.Image]::FromFile($full)
# 세로는 반칸 단위라 짝수로 맞춘다. 글자 칸이 세로로 길어 2 로 나눈다.
$height = [int][Math]::Round($src.Height * $Width / $src.Width / 2) * 2
if ($height -lt 2) { $height = 2 }
$bmp = New-Object System.Drawing.Bitmap($src, $Width, $height)
$src.Dispose()

$esc = [char]27
$upperHalf = [char]0x2580
$out = New-Object System.Text.StringBuilder

for ($y = 0; $y -lt $height; $y += 2) {
    for ($x = 0; $x -lt $Width; $x++) {
        $top = $bmp.GetPixel($x, $y)
        $bottom = $bmp.GetPixel($x, $y + 1)
        [void]$out.Append("$esc[38;2;$($top.R);$($top.G);$($top.B)m")
        [void]$out.Append("$esc[48;2;$($bottom.R);$($bottom.G);$($bottom.B)m")
        [void]$out.Append($upperHalf)
    }
    [void]$out.AppendLine("$esc[0m")
}

$bmp.Dispose()
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$out.ToString()
