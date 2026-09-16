@echo off
title FluxoV2 LIVE DEMO - XAUUSD
cd /d D:\proyectos_javier\proyectos\xauusd-trader
echo === FASE 4 LIVE DEMO CONTINUO (Ctrl+C para parar) ===
py live_demo.py --iter 400 --interval 60
pause