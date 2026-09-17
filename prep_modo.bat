@echo off
cd /d D:\proyectos_javier\proyectos\xauusd-trader
echo === REINICIO_PREP %date% %time% === > cert_reinicio.txt
powershell -NoProfile -Command "Set-Content -Path 'C:\Users\javie\AppData\Roaming\MetaQuotes\Terminal\Common\Files\fluxov2_mode.txt' -Value '0' -Encoding Unicode"
echo MODO_ESCRITO >> cert_reinicio.txt
py check_pos.py >> cert_reinicio.txt 2>&1
powershell -NoProfile -Command "$b=[System.IO.File]::ReadAllBytes('C:\Users\javie\AppData\Roaming\MetaQuotes\Terminal\Common\Files\fluxov2_mode.txt'); 'BYTES=' + $b.Length + ' HEX=' + (($b | ForEach-Object { $_.ToString('X2') }) -join ' ') >> D:\proyectos_javier\proyectos\xauusd-trader\cert_reinicio.txt"
echo PREP_LISTO >> cert_reinicio.txt