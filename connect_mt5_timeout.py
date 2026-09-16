"""Fase 0b: initialize con TIMEOUT real via thread (no se cuelga).
Uso: py connect_mt5_timeout.py
"""
import os, sys, threading
from dotenv import load_dotenv
load_dotenv()
LOGIN = os.getenv("MT5_LOGIN", "")
PASSWORD = os.getenv("MT5_PASSWORD", "")
SERVER = os.getenv("MT5_SERVER", "")
SYMBOL = os.getenv("MT5_SYMBOL", "XAUUSD")
MT5_PATH = os.getenv("MT5_PATH", r"D:\mt5\terminal64.exe")
import MetaTrader5 as mt5

res = {}
def do_init():
    try:
        if MT5_PATH and os.path.exists(MT5_PATH):
            res["ok"] = mt5.initialize(path=MT5_PATH, timeout=15000)
        else:
            res["ok"] = mt5.initialize(timeout=15000)
        res["err"] = mt5.last_error()
    except Exception as e:
        res["exc"] = str(e)

print("=== FASE 0b timeout ===", flush=True)
print(f"path={MT5_PATH} existe={os.path.exists(MT5_PATH)}", flush=True)
t = threading.Thread(target=do_init, daemon=True)
t.start()
t.join(timeout=30)
if t.is_alive():
    print("TIMEOUT 30s en initialize(). El terminal no responde al pipe IPC.", flush=True)
    print("Accion: cierra MT5, abrelo de nuevo logueado en Deriv-Demo, y reintenta.", flush=True)
    sys.exit(3)
print(f"initialize={res.get('ok')} err={res.get('err')} exc={res.get('exc')}", flush=True)
if not res.get("ok"):
    sys.exit(1)
print(f"version={mt5.version()}", flush=True)
ti = mt5.terminal_info()
print(f"terminal company={ti.company} path={ti.path} connected={ti.connected} trade_allowed={ti.trade_allowed}", flush=True)
for srv in [SERVER, "Deriv-Demo", "DerivSVG-Server", "Deriv-Server"]:
    print(f"login {srv} ...", flush=True)
    if mt5.login(int(LOGIN), password=PASSWORD, server=srv):
        print(f"LOGIN OK {srv}", flush=True)
        acc = mt5.account_info()
        print(f"cuenta login={acc.login} server={acc.server} balance={acc.balance} equity={acc.equity} lev=1:{acc.leverage} {acc.currency} mode={acc.trade_mode}", flush=True)
        syms = mt5.symbols_get("*XAU*")
        print(f"simbolos XAU: {[s.name for s in (syms or [])][:15]}", flush=True)
        syms2 = mt5.symbols_get("*GOLD*")
        print(f"simbolos GOLD: {[s.name for s in (syms2 or [])][:15]}", flush=True)
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick is None:
            mt5.symbol_select(SYMBOL, True)
            tick = mt5.symbol_info_tick(SYMBOL)
        print(f"tick {SYMBOL}: {tick}", flush=True)
        mt5.shutdown()
        print("FASE 0b OK", flush=True)
        sys.exit(0)
    else:
        print(f"  fallo {mt5.last_error()}", flush=True)
print("LOGIN fallo en todos", flush=True)
mt5.shutdown()
sys.exit(1)
