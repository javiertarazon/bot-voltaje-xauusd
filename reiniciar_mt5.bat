@echo off
cd /d D:\proyectos_javier\proyectos\xauusd-trader
echo === REINICIO_MT5 %date% %time% === > cert_reinicio2.txt
taskkill /IM terminal64.exe >> cert_reinicio2.txt 2>&1
echo --- esperando cierre --- >> cert_reinicio2.txt
timeout /t 25 /nobreak > NUL
tasklist /FI "IMAGENAME eq terminal64.exe" >> cert_reinicio2.txt 2>&1
echo --- relanzando --- >> cert_reinicio2.txt
start "" "D:\mt5\terminal64.exe"
timeout /t 75 /nobreak > NUL
powershell -NoProfile -Command "$p=Get-Process terminal64 -ErrorAction SilentlyContinue; if($p){'TERMINAL_VIVO PID=' + $p.Id} else {'TERMINAL_NO_ARRANCO'} | Out-File -Append -FilePath 'D:\proyectos_javier\proyectos\xauusd-trader\cert_reinicio2.txt' -Encoding utf8"
echo REINICIO_FIN >> cert_reinicio2.txt