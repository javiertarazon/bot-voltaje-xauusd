"""Fase 3: live paper + memoria SQLite + gestion riesgo viva. NO opera real.
Uso: py live_paper.py --iter 20
Lee .env, conecta MT5, calcula flujo+Bayes+MC en vivo, decide BUY/SELL/FLAT,
calcula lote por riesgo, guarda en trading_log.db (trades paper + no_trades).
"""
import os, sys, json, sqlite3, argparse
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from dotenv import load_dotenv
load_dotenv()
BASE = Path(__file__).parent
CFG = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
DB = BASE / "trading_log.db"
LOGIN = os.getenv("MT5_LOGIN", ""); PASSWORD = os.getenv("MT5_PASSWORD", "")
SERVER = os.getenv("MT5_SERVER", "Deriv-Demo"); SYMBOL = os.getenv("MT5_SYMBOL", "XAUUSD")
MT5_PATH = os.getenv("MT5_PATH", r"D:\mt5\terminal64.exe")
import MetaTrader5 as mt5

# Umbrales elegidos por Fase 2b (mejor expectancy)
UZ, PM = 1.0, 0.55
RISK_PCT = float(CFG.get("risk_pct_por_trade", 0.5))

def db_init():
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS paper_trades(
      id INTEGER PRIMARY KEY, ts TEXT, symbol TEXT, lado TEXT, entry REAL, sl REAL, tp REAL,
      lote REAL, z REAL, p_up REAL, p_mc REAL, motivo TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS no_trades(
      id INTEGER PRIMARY KEY, ts TEXT, symbol TEXT, z REAL, p_up REAL, p_mc REAL, razon TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS equity(
      id INTEGER PRIMARY KEY, ts TEXT, balance REAL, equity REAL)""")
    c.commit(); c.close()

def flujo_live(df):
    px = df["close"].astype(float)
    vol = df["tick_volume"].astype(float) if "tick_volume" in df.columns else pd.Series(1.0, index=df.index)
    ret = px.diff().fillna(0.0)
    atr = (px.rolling(14).max() - px.rolling(14).min()).bfill().fillna(1.0)
    vol_med = vol.rolling(50).mean().bfill().fillna(1.0) + 1e-9
    R = atr / vol_med; I = ret / (R + 1e-9)
    C = (px.rolling(20).max() - px.rolling(20).min()).fillna(0.0)
    Q = (np.sign(ret) * vol).rolling(20).sum().fillna(0.0)
    z = ((I - I.rolling(100).mean()) / (I.rolling(100).std() + 1e-9)).fillna(0.0)
    return px, I, R, C, Q, z, atr

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--iter", type=int, default=5)
    a = ap.parse_args()
    db_init()
    print("=== FASE 3 live paper ===", flush=True)
    if not mt5.initialize(path=MT5_PATH, timeout=20000):
        print(f"ERR initialize {mt5.last_error()}", flush=True); sys.exit(1)
    if not mt5.login(int(LOGIN), password=PASSWORD, server=SERVER):
        print(f"ERR login {mt5.last_error()}", flush=True); mt5.shutdown(); sys.exit(1)
    acc = mt5.account_info()
    print(f"cuenta {acc.login} bal={acc.balance} eq={acc.equity}", flush=True)
    mt5.symbol_select(SYMBOL, True)
    info = mt5.symbol_info(SYMBOL)
    tick0 = mt5.symbol_info_tick(SYMBOL)
    print(f"tick bid={tick0.bid} ask={tick0.ask} spread={info.spread}", flush=True)
    for k in range(a.iter):
        rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M15, 0, 300)
        if rates is None or len(rates) < 150:
            print(f"iter{k} sin velas {mt5.last_error()}", flush=True); continue
        df = pd.DataFrame(rates)
        px, I, R, C, Q, z, atr = flujo_live(df)
        # Bayes rapido ultimos 150
        qm = abs(Q).rolling(50, min_periods=1).mean() + 1e-9
        like = (0.5 + 0.3*np.tanh(Q/qm) + 0.2*np.tanh(z/2.0)).clip(0.05, 0.95)
        p = 0.5; lam = 0.98
        for li in like.iloc[-150:]:
            prev = lam*p + (1-lam)*0.5; li = float(li)
            p = li*prev/(li*prev + (1-li)*(1-prev) + 1e-12)
        zv, pv = float(z.iloc[-1]), float(p)
        # Monte Carlo corto
        win = px.iloc[-100:].values
        lr = np.diff(np.log(win + 1e-12)); mu, sg = float(np.mean(lr)), float(np.std(lr) + 1e-9)
        av = float(atr.iloc[-1]); p0 = float(px.iloc[-1])
        paths = p0*np.exp(np.cumsum(np.random.normal(mu, sg, (1000, 20)), axis=1))
        p_mc = float((((paths.max(1) >= p0+av)) & ~((paths.min(1) <= p0-0.7*av))).mean())
        lado = "FLAT"
        if zv > UZ and pv > PM and p_mc > 0.30: lado = "BUY"
        elif zv < -UZ and pv < 1-PM: lado = "SELL"
        ts = datetime.now(timezone.utc).isoformat()
        c = sqlite3.connect(DB)
        if lado == "FLAT":
            c.execute("INSERT INTO no_trades(ts,symbol,z,p_up,p_mc,razon) VALUES(?,?,?,?,?,?)",
                      (ts, SYMBOL, zv, pv, p_mc, f"z={zv:.2f} p={pv:.2f} mc={p_mc:.2f}"))
            print(f"[{k}] FLAT z={zv:.2f} p_up={pv:.3f} mc={p_mc:.2f}", flush=True)
        else:
            # lote por riesgo
            sl_dist = 0.8*av
            tick_val, tick_size = float(info.trade_tick_value), float(info.trade_tick_size)
            riesgo_usd = acc.balance * RISK_PCT/100.0
            lote = riesgo_usd / ((sl_dist/tick_size)*tick_val + 1e-9)
            lote = max(float(info.volume_min), min(float(info.volume_max), round(lote/int(1/info.volume_step))*(1/info.volume_step) if info.volume_step else round(lote,2)))
            entry = tick0.ask if lado=="BUY" else tick0.bid
            sl = entry - (1 if lado=="BUY" else -1)*sl_dist
            tp = entry + (1 if lado=="BUY" else -1)*1.2*av*1.5
            c.execute("INSERT INTO paper_trades(ts,symbol,lado,entry,sl,tp,lote,z,p_up,p_mc,motivo) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                      (ts, SYMBOL, lado, entry, sl, tp, lote, zv, pv, p_mc, "paper flux+mc"))
            print(f"[{k}] PAPER {lado} entry={entry:.2f} sl={sl:.2f} tp={tp:.2f} lote={lote} z={zv:.2f} p={pv:.3f} mc={p_mc:.2f}", flush=True)
        c.execute("INSERT INTO equity(ts,balance,equity) VALUES(?,?,?)", (ts, acc.balance, acc.equity))
        c.commit(); c.close()
        import time; time.sleep(2)
    mt5.shutdown()
    print(f"FASE 3 OK db={DB}", flush=True)

if __name__ == "__main__":
    main()
