"""Fase 1b: descarga M15 + M5 + ticks con timeout por thread + symbol_select.
Uso: py download_history_timeout.py (genera cert_fase1b.txt si se redirige)
"""
import os, sys, threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
import json
BASE = Path(__file__).parent
CFG = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
DATA = BASE / CFG.get("data_dir", "data")
DATA.mkdir(exist_ok=True)
LOGIN = os.getenv("MT5_LOGIN", "")
PASSWORD = os.getenv("MT5_PASSWORD", "")
SERVER = os.getenv("MT5_SERVER", "Deriv-Demo")
SYMBOL = os.getenv("MT5_SYMBOL", "XAUUSD")
MT5_PATH = os.getenv("MT5_PATH", r"D:\mt5\terminal64.exe")
import MetaTrader5 as mt5
import pandas as pd

res = {}
def do_init():
    try:
        res["ok"] = mt5.initialize(path=MT5_PATH, timeout=15000)
        res["err"] = mt5.last_error()
    except Exception as e:
        res["exc"] = str(e)

print("=== FASE 1b ===", flush=True)
t = threading.Thread(target=do_init, daemon=True); t.start(); t.join(timeout=40)
if t.is_alive():
    print("TIMEOUT initialize 40s", flush=True); sys.exit(3)
print(f"initialize={res.get('ok')} err={res.get('err')}", flush=True)
if not res.get("ok"): sys.exit(1)
if not mt5.login(int(LOGIN), password=PASSWORD, server=SERVER):
    print(f"login fallo {mt5.last_error()} reintentando Deriv-Demo...", flush=True)
    if not mt5.login(int(LOGIN), password=PASSWORD, server="Deriv-Demo"):
        print(f"ERROR login {mt5.last_error()}", flush=True); mt5.shutdown(); sys.exit(1)
print("login OK", flush=True)
# Seleccionar simbolo (tick en 0 indica no seleccionado / mercado cerrado)
if not mt5.symbol_select(SYMBOL, True):
    print(f"symbol_select fallo {mt5.last_error()}", flush=True)
info = mt5.symbol_info(SYMBOL)
print(f"symbol {info.name} digits={info.digits} spread={info.spread} trade_mode={info.trade_mode}", flush=True)
tick = mt5.symbol_info_tick(SYMBOL)
print(f"tick bid={tick.bid} ask={tick.ask} time={tick.time}", flush=True)

fin = datetime.now(timezone.utc)
inicio = datetime.strptime(CFG["fecha_inicio_historia"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
print(f"rango {inicio.date()} -> {fin.date()}", flush=True)
ok_n = 0
for tf_name, tf in [("M15", mt5.TIMEFRAME_M15), ("M5", mt5.TIMEFRAME_M5), ("M1", mt5.TIMEFRAME_M1)]:
    print(f"descargando {tf_name} ...", flush=True)
    holder = {}
    def dl(tf=tf, holder=holder):
        try:
            holder["rates"] = mt5.copy_rates_range(SYMBOL, tf, inicio, fin)
        except Exception as e:
            holder["exc"] = str(e)
    th = threading.Thread(target=dl, daemon=True); th.start(); th.join(timeout=180)
    if th.is_alive():
        print(f"  TIMEOUT 180s en {tf_name}, salto al siguiente", flush=True); continue
    rates = holder.get("rates")
    if rates is None or len(rates) == 0:
        print(f"  sin datos {tf_name}: {mt5.last_error()} exc={holder.get('exc')}", flush=True); continue
    df = pd.DataFrame(rates); df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    ruta = DATA / f"xauusd_{tf_name}.csv"; df.to_csv(ruta, index=False); ok_n += 1
    print(f"  OK {tf_name}: {len(df)} velas {df['time'].iloc[0]} -> {df['time'].iloc[-1]} -> {ruta}", flush=True)

print("ticks 30d ...", flush=True)
holder = {}
def dl_ticks(holder=holder):
    try:
        holder["t"] = mt5.copy_ticks_range(SYMBOL, fin - timedelta(days=30), fin, mt5.COPY_TICKS_ALL)
    except Exception as e:
        holder["exc"] = str(e)
th = threading.Thread(target=dl_ticks, daemon=True); th.start(); th.join(timeout=180)
if th.is_alive():
    print("  TIMEOUT ticks 180s", flush=True)
else:
    tks = holder.get("t")
    if tks is not None and len(tks) > 0:
        tdf = pd.DataFrame(tks)
        if len(tdf) > 500000: tdf = tdf.tail(500000)
        ruta_t = DATA / "xauusd_ticks_30d.csv"; tdf.to_csv(ruta_t, index=False); ok_n += 1
        print(f"  OK ticks: {len(tdf)} filas -> {ruta_t}", flush=True)
    else:
        print(f"  sin ticks: {mt5.last_error()} exc={holder.get('exc')}", flush=True)
mt5.shutdown()
print(f"FASE 1b OK archivos={ok_n}", flush=True)
sys.exit(0 if ok_n else 1)
