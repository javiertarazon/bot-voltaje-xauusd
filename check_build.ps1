$log = 'C:\Users\javie\AppData\Roaming\MetaQuotes\Terminal\Common\Files\fluxov2_ea.log'
$c = Get-Content $log
$o = @()
$o += "AHORA=" + (Get-Date -Format 'HH:mm:ss')
$o += "LINEAS=" + $c.Count
foreach ($pat in @('16sep-D','16sep-C','EA INIT','MODE EFECTIVO','mode=')) {
    $m = $c | Select-String -Pattern $pat -SimpleMatch
    $o += "PAT[$pat] = " + $m.Count
    if ($m.Count -gt 0) { $o += "   ult: " + $m[-1].Line.Trim() }
}
$o | Out-File -FilePath 'D:\proyectos_javier\proyectos\xauusd-trader\cert_build.txt' -Encoding utf8