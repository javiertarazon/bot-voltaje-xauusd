$procs = Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('py.exe','python.exe') }
$out = @()
foreach ($p in $procs) {
    $cl = $p.CommandLine
    if ($cl -and ($cl -like '*live_demo*' -or $cl -like '*test_order*')) {
        $out += "KILL PID=$($p.ProcessId) CMD=$cl"
        Stop-Process -Id $p.ProcessId -Force
    } else {
        $out += "SKIP PID=$($p.ProcessId) CMD=$cl"
    }
}
if (-not $procs) { $out += "NO_PYTHON_PROCS" }
$out | Out-File -FilePath 'D:\proyectos_javier\proyectos\xauusd-trader\cert_kill.txt' -Encoding utf8