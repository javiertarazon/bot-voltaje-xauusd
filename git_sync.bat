@echo off
cd /d D:\proyectos_javier\proyectos\xauusd-trader
echo === GIT SYNC %date% %time% === > cert_git2.txt
git add -A >> cert_git2.txt 2>&1
git -c user.name=Javier -c user.email=javiertarazon@users.noreply.github.com commit -m "EA sincronizado: log de config en INIT y parser UTF-16; scripts de verificacion" >> cert_git2.txt 2>&1
git push origin main >> cert_git2.txt 2>&1
echo --- REMOTO --- >> cert_git2.txt
git log origin/main -1 --oneline >> cert_git2.txt 2>&1
git status --short >> cert_git2.txt 2>&1
echo GIT_DONE >> cert_git2.txt