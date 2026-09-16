$c = Get-Content 'D:\proyectos_javier\proyectos\xauusd-trader\cert_publish.txt'
$out = @()
$out += "TOTAL_LINEAS=" + $c.Count
$out += "--- ULTIMAS 25 ---"
$out += ($c | Select-Object -Last 25)
$out | Out-File -FilePath 'D:\proyectos_javier\proyectos\xauusd-trader\cert_pubtail.txt' -Encoding utf8