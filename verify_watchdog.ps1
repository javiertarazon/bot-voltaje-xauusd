$tail = Get-Content 'D:\proyectos_javier\proyectos\xauusd-trader\cert_fase4.txt' -Tail 7
$wds = Get-CimInstance Win32_Process -Filter "Name='cmd.exe'" | Where-Object { $_.CommandLine -like '*correr_demo_loop*' }
$py = Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('py.exe','python.exe') }
$datos = @()
$datos += "=== WATCHDOGS_VIVOS: " + @($wds).Count
foreach ($w in $wds) { $datos += "  WD PID=$($w.ProcessId) INI=$($w.CreationDate)" }
$datos += "=== PYTHON_VIVOS: " + @($py).Count
foreach ($p in $py) { $datos += "  PY PID=$($p.ProcessId) CMD=$($p.CommandLine)" }
$datos += "=== TAIL_LOG ==="
$datos += $tail
$datos | Out-File -FilePath 'D:\proyectos_javier\proyectos\xauusd-trader\cert_verify.txt' -Encoding utf8