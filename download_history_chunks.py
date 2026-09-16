"""Fase 1c: descarga M15/M5/M1 por CHUNKS anuales (evita Invalid params por rango gigante).
Uso: py download_history_chunks.py
"""
import os, sys, threading
from datetime import datetime, timezone
from pathlib import Path
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
load_dotenv()
import json
BASE = Path(__file__).parent
CFG = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
DATA = BASE / CFG.get("data_dir", "data")
DATA.mkdir(exist_ok=True)
LOGIN = os.getenv("MT5_LOGIN", ""); PASSWORD = os.getenv("MT5_PASSWORD", "")
SERVER = os.getenv("MT5_SERVER", "Deriv-Demo"); SYMBOL = os.getenv("MT5_SYMBOL", "XAUUSD")
MT5_PATH = os.getenv("MT5_PATH", r"D:\mt5\terminal64.exe")
import MetaTrader5 as mt5
import pandas as pd

res = {}
def do_init():
    try:
        res["ok"] = mt5.initialize(path=MT5_PATH, timeout=20000)
        res["err"] = mt5.last_error()
    except Exception as e:
        res["exc"] = str(e)
print("=== FASE 1c chunks ===", flush=True)
t = threading.Thread(target=do_init, daemon=True); t.start(); t.join(timeout=45)
if t.is_alive(): print("TIMEOUT initialize", flush=True); sys.exit(3)
print(f"initialize={res.get('ok')} {res.get('err')}", flush=True)
if not res.get("ok"): sys.exit(1)
if not mt5.login(int(LOGIN), password=PASSWORD, server=SERVER):
    print(f"login fallo {mt5.last_error()}", flush=True); mt5.shutdown(); sys.exit(1)
print("login OK", flush=True)
mt5.symbol_select(SYMBOL, True)

fin_global = datetime.now(timezone.utc)
inicio_global = datetime.strptime(CFG["fecha_inicio_historia"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
total = 0
for tf_name, tf in [("M15", mt5.TIMEFRAME_M15), ("M5", mt5.TIMEFRAME_M5)]:
    print(f"== {tf_name} por anios ==", flush=True)
    trozos = []
    ini = inicio_global
    while ini < fin_global:
        nxt = min(ini + relativedelta(years=1), fin_global)
        holder = {}
        def dl(holder=holder, tf=tf, a=ini, b=nxt):
            try: holder["r"] = mt5.copy_rates_range(SYMBOL, tf, a, b)
            except Exception as e: holder["exc"] = str(e)
        th = threading.Thread(target=dl, daemon=True); th.start(); th.join(timeout=120)
        if th.is_alive():
            print(f"  {ini.date()}->{nxt.date()} TIMEOUT", flush=True)
        else:
            r = holder.get("r")
            if r is not None and len(r) > 0:
                print(f"  {ini.date()}->{nxt.date()} {len(r)} velas", flush=True)
                trozos.append(pd.DataFrame(r))
            else:
                print(f"  {ini.date()}->{nxt.date()} vacio {mt5.last_error()}", flush=True)
        ini = nxt
    if trozos:
        df = pd.concat(trozos, ignore_index=True).drop_duplicates("time").sort_values("time")
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        ruta = DATA / f"xauusd_{tf_name}.csv"; df.to_csv(ruta, index=False); total += 1
        print(f"OK {tf_name}: {len(df)} velas {df['time'].iloc[0]} -> {df['time'].iloc[-1]} -> {ruta}", flush=True)
    else:
        print(f"SIN DATOS {tf_name}", flush=True)
mt5.shutdown()
print(f"FASE 1c OK archivos={total}", flush=True)
sys.exit(0 if total else 1)
