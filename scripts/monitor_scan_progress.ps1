# 大三城报刊扫描实时进度条（终端页查看）
# 用法：在终端 tab 运行  powershell -ExecutionPolicy Bypass -File scripts\monitor_scan_progress.ps1
# 每 3 秒读 data\cleaned\newspaper\scan_progress.json 并刷新进度条；pct>=100 自动退出；可随时 Ctrl+C。
$projectRoot = Split-Path -Parent $PSScriptRoot
$json = Join-Path $projectRoot 'data\cleaned\newspaper\scan_progress.json'
$barLen = 40
while ($true) {
    if (Test-Path -LiteralPath $json) {
        try {
            $p = Get-Content -LiteralPath $json -Encoding UTF8 | ConvertFrom-Json
        } catch { Start-Sleep -Seconds 3; continue }
        $pct = [math]::Round([double]$p.pct, 1)
        $filled = [math]::Round($barLen * $pct / 100)
        $bar = ('#' * $filled) + ('-' * ($barLen - $filled))
        $line = ("Scan {0,5}% [{1}] {2}/{3}  rate={4}/s  ETA={5} min" -f
                 $pct, $bar, $p.processed, $p.total,
                 [math]::Round([double]$p.rate, 1), [math]::Round([double]$p.eta / 60, 1))
        Write-Host ("`r{0}" -f $line) -NoNewline
        if ([double]$p.pct -ge 100) { Write-Host ""; Write-Host "DONE"; break }
    } else {
        Write-Host ("`rwaiting for scan_progress.json ...") -NoNewline
    }
    Start-Sleep -Seconds 3
}
