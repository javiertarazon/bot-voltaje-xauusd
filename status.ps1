$o = @()
$o += "AHORA=" + (Get-Date -Format 'HH:mm:ss')
$log = 'C:\Users\javie\AppData\Roaming\MetaQuotes\Terminal\Common\Files\fluxov2_ea.log'
$sig = 'C:\Users\javie\AppData\Roaming\MetaQuotes\Terminal\Common\Files\fluxov2_signal.json'
$pub = 'D:\proyectos_javier\proyectos\xauusd-trader\cert_publish.txt'
foreach ($f in @($log,$sig,$pub)) {
    if (Test-Path $f) { $o += "MTIME " + (Split-Path $f -Leaf) + " = " + (Get-Item $f).LastWriteTime }
    else { $o += "FALTA " + (Split-Path $f -Leaf) }
}
$c = Get-Content $log
$o += "LOG_LINEAS=" + $c.Count
$o += "--- ULTIMAS 3 LOG ---"
$o += ($c | Where-Object { $_.Trim() -ne '' } | Select-Object -Last 3 | ForEach-Object { $_.Trim() })
$o += "--- PYTHON ---"
foreach ($p in (Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('py.exe','python.exe') })) {
    $o += "PID=" + $p.ProcessId + " CMD=" + $p.CommandLine
}
$o += "--- CMD WATCHDOGS ---"
foreach ($p in (Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'cmd.exe' -and ($_.CommandLine -like '*publish*' -or $_.CommandLine -like '*demo_loop*') })) {
    $o += "PID=" + $p.ProcessId + " CMD=" + $p.CommandLine
}
$o += "--- TERMINAL MT5 ---"
foreach ($p in (Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'terminal64.exe' })) {
    $o += "PID=" + $p.ProcessId
}
$o | Out-File -FilePath 'D:\proyectos_javier\proyectos\xauusd-trader\cert_status.txt' -Encoding utf8