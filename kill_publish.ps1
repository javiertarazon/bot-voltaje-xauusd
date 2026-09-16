$procs = Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('py.exe','python.exe') }
$out = @()
foreach ($p in $procs) {
    $cl = $p.CommandLine
    if ($cl -and $cl -like '*live_publish*') {
        Stop-Process -Id $p.ProcessId -Force
    } else {
        $out += "SKIP PID=$($p.ProcessId) CMD=$cl"
    }
}
$out | Out-File -FilePath 'D:\proyectos_javier\proyectos\xauusd-trader\cert_kill_pub.txt' -Encoding utf8