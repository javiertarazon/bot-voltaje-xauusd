@echo off
title FluxoV2 PUBLISH WATCHDOG
cd /d D:\proyectos_javier\proyectos\xauusd-trader
echo === PUBLISH WATCHDOG INICIO %date% %time% === >> cert_publish.txt
for /L %%i in (1,1,999999) do (
  echo === PUB %%i %date% %time% === >> cert_publish.txt
  start "" /min cmd /c "py live_publish.py --iter 1 --interval 10 >> cert_publish.txt 2>&1"
  timeout /t 60 /nobreak > NUL
  powershell -NoProfile -ExecutionPolicy Bypass -File kill_publish.ps1
  timeout /t 3 /nobreak > NUL
)