"""Diagnostico de rutas reales del terminal MT5 (portable en D:\\mt5)."""
import MetaTrader5 as mt5
from pathlib import Path

print("CARGANDO terminal ...", flush=True)
if not mt5.initialize(path=r"D:\mt5\terminal64.exe", timeout=20000):
    print(f"ERR init {mt5.last_error()}")
    raise SystemExit(1)
ti = mt5.terminal_info()
print(f"path          = {ti.path}")
print(f"data_path     = {ti.data_path}")
print(f"commondata_path = {ti.commondata_path}")
print(f"connected={ti.connected} trade_allowed={ti.trade_allowed}")
for base in (ti.data_path, ti.commondata_path, r"D:\mt5"):
    p = Path(base)
    print(f"--- existe={p.exists()} : {p}")
    if p.exists():
        for hijo in sorted(p.iterdir()):
            print(f"    {hijo.name}")
mt5.shutdown()
print("PROBE OK")
