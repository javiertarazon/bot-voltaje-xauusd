$ps = Get-CimInstance Win32_Process
$out = @()
$out += "--- PYTHON ---"
foreach ($p in $ps | Where-Object { $_.Name -in @('py.exe','python.exe') }) {
    $out += "PID=$($p.ProcessId) NAME=$($p.Name) CMD=$($p.CommandLine)"
}
$out += "--- CMD ---"
foreach ($p in $ps | Where-Object { $_.Name -eq 'cmd.exe' -and $_.CommandLine -like '*publish*' }) {
    $out += "PID=$($p.ProcessId) CMD=$($p.CommandLine)"
}
$out | Out-File -FilePath 'D:\proyectos_javier\proyectos\xauusd-trader\cert_procs.txt' -Encoding utf8