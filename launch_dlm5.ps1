$ErrorActionPreference = "SilentlyContinue"
Set-Location "D:\proyectos_javier\proyectos\xauusd-trader"
"LANZADO DLM5 $(Get-Date -Format 'HH:mm:ss')" | Out-File "cert_dlm5_launch.txt" -Encoding utf8
Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", "py download_m5_2024.py > cert_dlm5.txt 2>&1") -WindowStyle Minimized
"PROCESO DL LANZADO" | Out-File "cert_dlm5_launch.txt" -Encoding utf8 -Append
