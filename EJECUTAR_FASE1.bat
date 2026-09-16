@echo off
REM Fase 1 completa: M1/M5/M15 2022-hoy + ticks 30d. Doble click si el agente no puede.
cd /d d:\proyectos_javier\proyectos\xauusd-trader
echo Inicio: %DATE% %TIME% > cert_fase1_full.txt 2>&1
start /wait /min py download_history.py >> cert_fase1_full.txt 2>&1
echo EXIT_FASE1=%ERRORLEVEL% >> cert_fase1_full.txt 2>&1
echo Fin: %DATE% %TIME% >> cert_fase1_full.txt 2>&1
pause
