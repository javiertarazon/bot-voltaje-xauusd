"""Descarga M5 2024 desde MT5 con guardias anti-cuelgue. Uso: py download_m5_2024.py
Lee .env (MT5_PATH/LOGIN/PASSWORD/SERVER). Fusiona en data/xauusd_M5.csv.
"""
import os
import threading
import datetime as dtm
from pathlib import Path
import pandas as pd
BASE = Path(__file__).parent
DATA = BASE / "data"
DATA.mkdir(exist_ok=True)
def getenv(k, d=""):
    v = os.environ.get(k, d)
    envf = BASE / ".env"
    if envf.exists() and not v:
        for ln in envf.read_text(encoding="utf-8", errors="ignore").splitlines():
            ln = ln.strip()
            if ln.startswith(k + "="):
                return ln.split("=", 1)[1].strip().strip('"').strip("'")
    return v
def main():
    import MetaTrader5 as mt5
    path = getenv("MT5_PATH", r"D:\mt5\terminal64.exe")
    login = getenv("MT5_LOGIN", "")
    pwd = getenv("MT5_PASSWORD", "")
    srv = getenv("MT5_SERVER", "")
    sym = getenv("MT5_SYMBOL", "XAUUSD")
    print(f"INIT path={path} login={'***' if login else '(vacio)'} srv={srv}", flush=True)
    holder = {}
    def do_init():
        try:
            holder["ok"] = mt5.initialize(path=path) if path else mt5.initialize()
        except Exception as e:
            holder["exc"] = str(e)
    th = threading.Thread(target=do_init, daemon=True)
    th.start(); th.join(timeout=30)
    if not holder.get("ok"):
        print(f"INIT FAIL exc={holder.get('exc')} err={mt5.last_error()}", flush=True)
        return
    print("INIT OK", flush=True)
    if login and pwd and srv:
        holder2 = {}
        def do_login():
            try:
                holder2["ok"] = mt5.login(int(login), pwd, srv)
            except Exception as e:
                holder2["exc"] = str(e)
        th2 = threading.Thread(target=do_login, daemon=True)
        th2.start(); th2.join(timeout=30)
        print(f"LOGIN ok={holder2.get('ok')} exc={holder2.get('exc')} err={mt5.last_error()}", flush=True)
    import datetime as dtmod
    a = dtmod.datetime(2024, 1, 1, tzinfo=dtmod.timezone.utc)
    b = dtmod.datetime(2025, 1, 1, tzinfo=dtmod.timezone.utc)
    holder3 = {}
    def do_dl():
        try:
            holder3["r"] = mt5.copy_rates_range(sym, mt5.TIMEFRAME_M5, a, b)
        except Exception as e:
            holder3["exc"] = str(e)
    th3 = threading.Thread(target=do_dl, daemon=True)
    th3.start(); th3.join(timeout=150)
    r = holder3.get("r")
    print(f"DL exc={holder3.get('exc')} n={(len(r) if r is not None else 0)}", flush=True)
    if r is None or len(r) == 0:
        print(f"DL VACIO err={mt5.last_error()}", flush=True)
        try:
            mt5.shutdown()
        except Exception:
            pass
        return
    df = pd.DataFrame(r)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    keep = ["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
    df = df[[c for c in keep if c in df.columns]]
    out = DATA / "xauusd_M5.csv"
    if out.exists():
        old = pd.read_csv(out)
        old["time"] = pd.to_datetime(old["time"], utc=True)
        df = pd.concat([old, df], ignore_index=True).drop_duplicates(subset=["time"]).sort_values("time").reset_index(drop=True)
    df.to_csv(out, index=False)
    print(f"DL OK total_m5={len(df)} rango={df['time'].min()} -> {df['time'].max()}", flush=True)
    try:
        mt5.shutdown()
    except Exception:
        pass
if __name__ == "__main__":
    main()
