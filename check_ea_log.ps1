$log = 'C:\Users\javie\AppData\Roaming\MetaQuotes\Terminal\Common\Files\fluxov2_ea.log'
$sig = 'C:\Users\javie\AppData\Roaming\MetaQuotes\Terminal\Common\Files\fluxov2_signal.json'
$out = @()
if (Test-Path $log) {
    $c = Get-Content $log
    $out += "LOG_LINEAS=$($c.Count)"
    $inits = $c | Select-String -Pattern 'EA INIT'
    $out += "INIT_COUNT=$($inits.Count)"
    foreach ($i in $inits) { $out += "INIT> " + $i.Line.Trim() }
    $out += "--- ULTIMAS 4 LINEAS ---"
    $out += ($c | Where-Object { $_.Trim() -ne '' } | Select-Object -Last 4 | ForEach-Object { $_.Trim() })
    $out += "--- ULTIMO BEAT Y ERR ---"
    $out += ($c | Select-String -Pattern 'BEAT' | Select-Object -Last 1).Line
    $out += ($c | Select-String -Pattern 'senal_invalida_sin_epoch' | Select-Object -Last 1).Line
    $out += "LOG_MTIME=$((Get-Item $log).LastWriteTime)"
} else { $out += "SIN_LOG" }
if (Test-Path $sig) {
    $b = [System.IO.File]::ReadAllBytes($sig)
    $out += "SIG_BYTES=$($b.Length) PRIMEROS8=" + (($b[0..7] | ForEach-Object { $_.ToString('X2') }) -join ' ')
    $out += "SIG_MTIME=$((Get-Item $sig).LastWriteTime)"
    $out += "SIG_TXT=" + [System.Text.Encoding]::UTF8.GetString($b)
} else { $out += "SIN_SIG" }
$out | Out-File -FilePath 'D:\proyectos_javier\proyectos\xauusd-trader\cert_ealog.txt' -Encoding utf8