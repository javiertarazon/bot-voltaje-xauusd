@echo off
REM Certificacion anti-bloqueo MT5. Doble click este archivo.
REM Genera cert_resultado.txt sin colgar la terminal del agente.
cd /d d:\proyectos_javier\proyectos\xauusd-trader
echo Inicio: %DATE% %TIME% > cert_resultado.txt 2>&1
py --version >> cert_resultado.txt 2>&1
echo --- PIP LIST MT5 --- >> cert_resultado.txt 2>&1
py -m pip show MetaTrader5 >> cert_resultado.txt 2>&1
echo --- FASE 0 --- >> cert_resultado.txt 2>&1
timeout /t 2 /nobreak >nul
start /wait /min py connect_mt5.py >> cert_resultado.txt 2>&1
echo EXIT_FASE0=%ERRORLEVEL% >> cert_resultado.txt 2>&1
echo --- FASE 1 --- >> cert_resultado.txt 2>&1
start /wait /min py download_history.py >> cert_resultado.txt 2>&1
echo EXIT_FASE1=%ERRORLEVEL% >> cert_resultado.txt 2>&1
echo Fin: %DATE% %TIME% >> cert_resultado.txt 2>&1
echo TERMINADO - abre cert_resultado.txt
pause
