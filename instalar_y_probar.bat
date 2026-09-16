@echo off
REM Instalacion + Fase 0 + Fase 1 XAUUSD Trader. Genera logs en esta carpeta.
cd /d d:\proyectos_javier\proyectos\xauusd-trader
py --version > cert_instala_python.txt 2>&1
py -m pip install -r requirements.txt > cert_instala_pips.txt 2>&1
echo EXIT_PIPS=%ERRORLEVEL% >> cert_instala_pips.txt
py connect_mt5.py > cert_fase0.txt 2>&1
echo EXIT_FASE0=%ERRORLEVEL% >> cert_fase0.txt
py download_history.py > cert_fase1.txt 2>&1
echo EXIT_FASE1=%ERRORLEVEL% >> cert_fase1.txt
echo TERMINADO > cert_terminado.txt
