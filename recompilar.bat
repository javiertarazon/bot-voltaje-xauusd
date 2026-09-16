@echo off
cd /d D:\proyectos_javier\proyectos\xauusd-trader
echo === RECOMPILAR %date% %time% === > cert_recompilar.txt
py -m py_compile live_publish.py && echo SYNTAX_OK >> cert_recompilar.txt 2>&1 || echo SYNTAX_FAIL >> cert_recompilar.txt 2>&1
py -m py_compile live_demo.py && echo SYNTAX_DEMO_OK >> cert_recompilar.txt 2>&1 || echo SYNTAX_DEMO_FAIL >> cert_recompilar.txt 2>&1
del /q cert_compile.txt 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -File compilar_ea.ps1
echo COMPILE_DONE >> cert_recompilar.txt
powershell -NoProfile -Command "$f=Get-Item 'C:\Users\javie\AppData\Roaming\MetaQuotes\Terminal\D8E196A488CAFD45BB0BBB0BC09A258A\MQL5\Experts\FluxoV2_EA.ex5'; \"EX5 mtime=\" + $f.LastWriteTime + \" size=\" + $f.Length >> D:\proyectos_javier\proyectos\xauusd-trader\cert_recompilar.txt"
echo TODO_LISTO >> cert_recompilar.txt