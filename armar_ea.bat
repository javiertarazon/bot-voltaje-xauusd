@echo off
cd /d D:\proyectos_javier\proyectos\xauusd-trader
echo === ARMAR %date% %time% === >> cert_armar.txt
powershell -NoProfile -Command "Set-Content -Path 'C:\Users\javie\AppData\Roaming\MetaQuotes\Terminal\Common\Files\fluxov2_mode.txt' -Value '1' -Encoding Unicode"
py check_modo.py >> cert_armar.txt 2>&1
echo ARMADO >> cert_armar.txt