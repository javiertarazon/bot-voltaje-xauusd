"""Dump costes reales XAUUSD Deriv para backtest profesional. Uso: py dump_costs.py"""
import os
from dotenv import load_dotenv
load_dotenv()
LOGIN = os.getenv("MT5_LOGIN", ""); PASSWORD = os.getenv("MT5_PASSWORD", "")
SERVER = os.getenv("MT5_SERVER", "Deriv-Demo"); SYMBOL = os.getenv("MT5_SYMBOL", "XAUUSD")
MT5_PATH = os.getenv("MT5_PATH", r"D:\mt5\terminal64.exe")
import MetaTrader5 as mt5
print("=== COSTES REALES ===", flush=True)
assert mt5.initialize(path=MT5_PATH, timeout=20000), mt5.last_error()
assert mt5.login(int(LOGIN), password=PASSWORD, server=SERVER), mt5.last_error()
mt5.symbol_select(SYMBOL, True)
info = mt5.symbol_info(SYMBOL)
d = info._asdict()
for k in sorted(d.keys()):
    print(f"{k}={d[k]}", flush=True)
acc = mt5.account_info()
print(f"ACC balance={acc.balance} currency={acc.currency} lev={acc.leverage} comm={acc.commission if hasattr(acc,'commission') else 'n/a'}", flush=True)
tick = mt5.symbol_info_tick(SYMBOL)
print(f"TICK bid={tick.bid} ask={tick.ask} spread_pts={info.spread}", flush=True)
# Valor USD de 1.00 movimiento con 1.00 lote y con 0.01
print(f"CALC: 1.00 lote mueve {info.trade_tick_value/info.trade_tick_size if info.trade_tick_size else '?'} USD por 1.00 precio", flush=True)
mt5.shutdown()
print("DUMP OK", flush=True)
