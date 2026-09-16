$src = 'C:\Users\javie\AppData\Roaming\MetaQuotes\Terminal\D8E196A488CAFD45BB0BBB0BC09A258A\MQL5\Experts'
$out = 'D:\proyectos_javier\proyectos\xauusd-trader\cert_compile.txt'
$mq5 = Join-Path $src 'FluxoV2_EA.mq5'
$ex5 = Join-Path $src 'FluxoV2_EA.ex5'
$before = (Get-Date)
if (Test-Path $ex5) { Remove-Item $ex5 -Force }
$lines = @()
$p = Start-Process -FilePath 'D:\mt5\MetaEditor64.exe' -ArgumentList ('/compile:' + $mq5), ('/log:C:\Users\javie\compile_ea.log') -PassThru -Wait
$lines += "EXITCODE=$($p.ExitCode)"
if (Test-Path 'C:\Users\javie\compile_ea.log') { $lines += "--- LOG ---"; $lines += (Get-Content 'C:\Users\javie\compile_ea.log') }
else { $lines += "SIN_LOG_LOGPATH" }
if (Test-Path $ex5) {
  $f = Get-Item $ex5
  $lines += "EX5_OK size=$($f.Length) mtime=$($f.LastWriteTime) fresh=$($f.LastWriteTime -gt $before)"
} else { $lines += "EX5_NO_EXISTE" }
$lines | Out-File -FilePath $out -Encoding utf8