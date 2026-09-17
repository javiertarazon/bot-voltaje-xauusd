@echo off
cd /d D:\proyectos_javier\proyectos\xauusd-trader
echo === RELANZAR_PUB %date% %time% === >> cert_publish.txt
:loop
start "" /min cmd /c "py live_publish.py --iter 1 --interval 10 >> cert_publish.txt 2>&1"
timeout /t 75 /nobreak > NUL
powershell -NoProfile -ExecutionPolicy Bypass -File kill_publish.ps1
timeout /t 3 /nobreak > NUL
goto loop