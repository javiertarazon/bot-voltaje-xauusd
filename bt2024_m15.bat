@echo off
cd /d D:\proyectos_javier\proyectos\xauusd-trader
echo === BT2024 M15 INICIO %date% %time% === > cert_bt24m15.txt 2>&1
py bt2024_prep.py M15 >> cert_bt24m15.txt 2>&1
py bt2024_run.py M15 >> cert_bt24m15.txt 2>&1
py bt2024_plot.py M15 >> cert_bt24m15.txt 2>&1
echo EXIT=%ERRORLEVEL% FIN=%date% %time% >> cert_bt24m15.txt 2>&1
