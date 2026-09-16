@echo off
title FluxoV2 WATCHDOG DEMO
cd /d D:\proyectos_javier\proyectos\xauusd-trader
echo === WATCHDOG INICIO %date% %time% === >> cert_fase4.txt
:loop
echo === CICLO %date% %time% === >> cert_fase4.txt
start "" /min cmd /c "py live_demo.py --iter 1 --interval 10 >> cert_fase4.txt 2>&1"
timeout /t 90 /nobreak > NUL
powershell -NoProfile -ExecutionPolicy Bypass -File kill_live.ps1
timeout /t 5 /nobreak > NUL
goto loop