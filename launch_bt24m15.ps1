$ErrorActionPreference = "SilentlyContinue"
Set-Location "D:\proyectos_javier\proyectos\xauusd-trader"
"LANZADO BT24M15 $(Get-Date -Format 'HH:mm:ss')" | Out-File "cert_bt24m15_launch.txt" -Encoding utf8
Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", "bt2024_m15.bat") -WindowStyle Minimized
"PROCESO BT LANZADO" | Out-File "cert_bt24m15_launch.txt" -Encoding utf8 -Append
