@echo off
set OUT=D:\proyectos_javier\proyectos\xauusd-trader\cert_git.txt
del /q "%OUT%" 2>nul
echo === GIT VERSION === >> "%OUT%"
git --version >> "%OUT%" 2>&1 || echo NO_GIT >> "%OUT%"
echo === GH VERSION === >> "%OUT%"
gh --version >> "%OUT%" 2>&1 || echo NO_GH >> "%OUT%"
echo === IDENTIDAD === >> "%OUT%"
git config --global user.name >> "%OUT%" 2>&1
git config --global user.email >> "%OUT%" 2>&1
echo === WS_REPO === >> "%OUT%"
if exist D:\proyectos_javier\.git (echo WS_ES_REPO >> "%OUT%") else (echo WS_NO_REPO >> "%OUT%")
echo === PROY_REPO === >> "%OUT%"
if exist D:\proyectos_javier\proyectos\xauusd-trader\.git (echo PROY_ES_REPO >> "%OUT%") else (echo PROY_NO_REPO >> "%OUT%")
echo === AUTH GH === >> "%OUT%"
gh auth status >> "%OUT%" 2>&1
echo FIN >> "%OUT%"