@echo off
set OUT=D:\proyectos_javier\proyectos\xauusd-trader\cert_push.txt
cd /d D:\proyectos_javier\proyectos\xauusd-trader
del /q "%OUT%" 2>nul
echo === REMOTES === >> "%OUT%"
git remote -v >> "%OUT%" 2>&1
echo === PUSH === >> "%OUT%"
git push -u origin main >> "%OUT%" 2>&1
echo EXITCODE=%ERRORLEVEL% >> "%OUT%"
echo FIN >> "%OUT%"