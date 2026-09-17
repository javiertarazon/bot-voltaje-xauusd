"""Fase 4: live demo REAL en cuenta Deriv-Demo. Estrategia FluxoV2 (solo LONG).
Uso: py live_demo.py --iter 20 --interval 60
Seguridad: aborta si no es cuenta demo o si trade_allowed=False. Cortacircuitos:
  - riesgo 0.5%/trade (lote dinamico por SL), si DD>10% del peak -> 0.25%
  - max 3 trades/dia, perdida diaria max 2%, sesion 7-20 UTC, spread max 30 pts
  - una sola posicion a la vez, cierre forzado a las 60 velas M15 (15h)
Memoria: trading_log.db tablas demo_trades / no_trades / equity.
"""
import os, sys, json, sqlite3, time, argparse
from datetime import datetime, timezone, timedelta
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
from core.indicators import calcular_flujo, calcular_atr, calcular_bayes, calcular_monte_carlo
from core.risk import calcular_riesgo_adaptativo

UZ = float(CFG.get("uz", 1.0)); PM = float(CFG.get("pm", 0.55))
TPK = float(CFG.get("tp_k", 2.0)); SLK = float(CFG.get("sl_k", 0.8))
MAXHOLD_VELAS = int(CFG.get("max_hold", 60)); HOLD_SEC = MAXHOLD_VELAS * 15 * 60
H_INI, H_FIN = int(CFG.get("sesion_utc", [7, 20])[0]), int(CFG.get("sesion_utc", [7, 20])[1])
MAX_TRADES_DIA = int(CFG.get("max_trades_dia", 3)); MAX_LOSS_DIA_PCT = float(CFG.get("max_daily_loss_pct", 2.0))
PMC_MIN = float(CFG.get("backtest_params", {}).get("umbral_mc", 0.30))
RISK = float(CFG.get("risk_pct_por_trade", 0.5)) / 100.0
RISK_RED = float(CFG.get("risk_reducido_pct", 0.25)) / 100.0
DD_RED_PCT = 10.0
MAGIC = int(CFG.get("magic", 20260915))
SPREAD_MAX_PTS = 30

def db_init():
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS demo_trades(
      id INTEGER PRIMARY KEY, ts TEXT, symbol TEXT, lado TEXT, ticket INTEGER,
      entry REAL, sl REAL, tp REAL, lote REAL, z REAL, p_up REAL, p_mc REAL,
      riesgo_pct REAL, motivo TEXT, cierre TEXT, pnl REAL, exit_px REAL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS no_trades(
      id INTEGER PRIMARY KEY, ts TEXT, symbol TEXT, z REAL, p_up REAL, p_mc REAL, razon TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS equity(
      id INTEGER PRIMARY KEY, ts TEXT, balance REAL, equity REAL, riesgo_pct REAL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS estado(k TEXT PRIMARY KEY, v TEXT)""")
    try:
        c.execute("ALTER TABLE equity ADD COLUMN riesgo_pct REAL")
    except sqlite3.OperationalError:
        pass  # ya existe
    c.commit(); c.close()

def peak_previo():
    c = sqlite3.connect(DB)
    r = c.execute("SELECT MAX(equity) FROM equity").fetchone()[0]
    c.close()
    return float(r) if r else 0.0

def flujo_live(df):
    flujo = calcular_flujo(df)
    return df["close"].astype(float), flujo["Q"], flujo["z"], calcular_atr(df, 14)

def bayes_live(Q, z, n=150):
    return float(calcular_bayes(Q, z).iloc[-1])

def monte_carlo_live(px, atr, paths=1000, hor=20):
    return calcular_monte_carlo(px, float(atr.iloc[-1]), paths=paths, horizon=hor, seed=42)

def send_market(lote, sl, tp, comment="FluxoV2"):
    tick = mt5.symbol_info_tick(SYMBOL)
    base = {"symbol": SYMBOL, "volume": lote, "deviation": 30, "magic": MAGIC,
            "comment": comment, "type_time": mt5.ORDER_TIME_GTC}
    r = None
    for fill in (mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_RETURN):
        req = dict(base, action=mt5.TRADE_ACTION_DEAL, type=mt5.ORDER_TYPE_BUY,
                   price=tick.ask, sl=sl, tp=tp, type_filling=fill)
        r = mt5.order_send(req)
        if r is not None and r.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED):
            return r, fill
    return r, None

def cerrar_pos(pos):
    tick = mt5.symbol_info_tick(SYMBOL)
    base = {"action": mt5.TRADE_ACTION_DEAL, "position": pos.ticket, "symbol": SYMBOL,
            "volume": pos.volume, "deviation": 30, "magic": MAGIC, "comment": "timeout/maxhold",
            "type_time": mt5.ORDER_TIME_GTC}
    for fill in (mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_RETURN):
        req = dict(base, type=mt5.ORDER_TYPE_SELL, price=tick.bid, type_filling=fill)
        r = mt5.order_send(req)
        if r is not None and r.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED):
            return True
    return False

def registrar_demo(ts, sig, cierre):
    c = sqlite3.connect(DB)
    c.execute("""INSERT INTO demo_trades(ts,symbol,lado,ticket,entry,sl,tp,lote,z,p_up,p_mc,
      riesgo_pct,motivo,cierre) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
      (ts, SYMBOL, sig.get("lado"), sig.get("ticket"), sig.get("entry"), sig.get("sl"),
       sig.get("tp"), sig.get("lote"), sig.get("z"), sig.get("p_up"), sig.get("p_mc"),
       sig.get("riesgo_pct"), sig.get("motivo"), cierre))
    c.commit(); c.close()

def actualizar_cierre(ticket, pnl, exit_px, cierre):
    c = sqlite3.connect(DB)
    c.execute("UPDATE demo_trades SET pnl=?, exit_px=?, cierre=? WHERE ticket=? AND cierre='abierta'",
              (pnl, exit_px, cierre, ticket))
    n = c.execute("SELECT changes()").fetchone()[0]
    c.commit(); c.close()
    return int(n)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iter", type=int, default=20)
    ap.add_argument("--interval", type=int, default=60)
    a = ap.parse_args()
    db_init()
    print("=== FASE 4 LIVE DEMO FluxoV2 ===", flush=True)
    if not mt5.initialize(path=MT5_PATH, timeout=20000):
        print(f"ERR initialize {mt5.last_error()}", flush=True); sys.exit(1)
    if not mt5.login(int(LOGIN), password=PASSWORD, server=SERVER):
        print(f"ERR login {mt5.last_error()}", flush=True); mt5.shutdown(); sys.exit(1)
    acc = mt5.account_info(); ti = mt5.terminal_info()
    if acc.trade_mode != 0:
        print(f"ABORT trade_mode={acc.trade_mode} NO es demo", flush=True); mt5.shutdown(); sys.exit(2)
    if not ti.trade_allowed:
        print("ABORT trading algoritmico desactivado", flush=True); mt5.shutdown(); sys.exit(2)
    print(f"DEMO OK cuenta {acc.login} bal={acc.balance} eq={acc.equity} lev=1:{acc.leverage}", flush=True)
    if not mt5.symbol_select(SYMBOL, True):
        print(f"ERR select {SYMBOL}", flush=True); mt5.shutdown(); sys.exit(1)
    info = mt5.symbol_info(SYMBOL)
    print(f"simbolo {SYMBOL} spread={info.spread} vmin={info.volume_min} vstep={info.volume_step}", flush=True)
    pos_sig = None
    for k in range(a.iter):
        ts = datetime.now(timezone.utc).isoformat()
        rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M15, 0, 300)
        acc = mt5.account_info()
        c = sqlite3.connect(DB)
        c.execute("INSERT INTO equity(ts,balance,equity,riesgo_pct) VALUES(?,?,?,?)",
                  (ts, acc.balance, acc.equity, RISK*100)); c.commit(); c.close()
        if rates is None or len(rates) < 150:
            print(f"[{k}] sin velas {mt5.last_error()}", flush=True); time.sleep(a.interval); continue
        df = pd.DataFrame(rates)
        df_c = df.iloc[:-1].reset_index(drop=True)   # ultima vela CERRADA, igual que backtest
        px, Q, z, atr = flujo_live(df_c)
        zv, av = float(z.iloc[-1]), float(atr.iloc[-1])
        pv = bayes_live(Q, z); p_mc = monte_carlo_live(px, atr)
        hora = datetime.now(timezone.utc).hour
        bal = acc.balance
        d0 = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        deals = mt5.history_deals_get(d0, d0 + timedelta(days=2)) or []
        outs = [d for d in deals if d.magic == MAGIC and d.entry == mt5.DEAL_ENTRY_OUT]
        d0ts = d0.timestamp()
        n_dia = len([d for d in deals if d.magic == MAGIC and d.entry == mt5.DEAL_ENTRY_IN and d.time >= d0ts])
        pnl_dia = sum(d.profit for d in outs if d.time >= d0ts)
        # --- deteccion de cierres por SL/TP ejecutados por el servidor ---
        c = sqlite3.connect(DB)
        row = c.execute("SELECT v FROM estado WHERE k='last_out_ticket'").fetchone()
        last_out = int(row[0]) if row else 0
        c.close()
        for d in sorted(outs, key=lambda x: x.ticket):
            if d.ticket <= last_out:
                continue
            tp_r, sl_r = (None, None)
            if pos_sig and pos_sig.get("tp") is not None:
                tp_r, sl_r = pos_sig.get("tp"), pos_sig.get("sl")
            else:
                c2 = sqlite3.connect(DB)
                fila = c2.execute("SELECT tp, sl FROM demo_trades WHERE ticket=? ORDER BY id DESC LIMIT 1",
                                  (d.position_id,)).fetchone()
                c2.close()
                if fila:
                    tp_r, sl_r = fila[0], fila[1]
            if tp_r is not None and sl_r is not None:
                cierre = "tp" if abs(d.price - tp_r) <= abs(d.price - sl_r) else "sl"
            else:
                cierre = "cierre_manual"
            n = actualizar_cierre(d.position_id, float(d.profit), float(d.price), cierre)
            c = sqlite3.connect(DB)
            c.execute("INSERT OR REPLACE INTO estado(k,v) VALUES('last_out_ticket',?)", (str(d.ticket),))
            c.commit(); c.close()
            print(f"[{k}] CIERRE REG ticket={d.ticket} tipo={cierre} pnl={d.profit:.2f} px={d.price:.2f}", flush=True)
            pos_sig = None
        poss = mt5.positions_get(symbol=SYMBOL) or []
        mias = [p for p in poss if p.magic == MAGIC]
        if mias:
            pos = mias[0]
            c2 = sqlite3.connect(DB)
            existe = c2.execute("SELECT 1 FROM demo_trades WHERE ticket=?", (pos.ticket,)).fetchone()
            c2.close()
            if not existe:
                registrar_demo(datetime.now(timezone.utc).isoformat(),
                               {"lado": "BUY", "ticket": pos.ticket, "entry": pos.price_open, "sl": pos.sl,
                                "tp": pos.tp, "lote": pos.volume, "z": 0.0, "p_up": 0.0, "p_mc": 0.0,
                                "riesgo_pct": 0.0, "motivo": "RECUPERADA_HUERFANA"}, "abierta")
                print(f"[{k}] RECUPERADA posicion huerfana ticket={pos.ticket} entry={pos.price_open}", flush=True)
            edad = datetime.now(timezone.utc) - datetime.fromtimestamp(pos.time, tz=timezone.utc)
            if edad.total_seconds() >= HOLD_SEC:
                ok = cerrar_pos(pos)
                print(f"[{k}] CIERRE MAXHOLD ticket={pos.ticket} ok={ok}", flush=True)
                if ok:
                    actualizar_cierre(pos.ticket, float(pos.profit), float(pos.price_current), "maxhold")
                    pos_sig = None
            else:
                print(f"[{k}] POS ticket={pos.ticket} vol={pos.volume} entry={pos.price_open} sl={pos.sl} "
                      f"tp={pos.tp} pnl={pos.profit:.2f} edad={int(edad.total_seconds()//60)}min", flush=True)
            time.sleep(a.interval); continue
        peak = max(peak_previo(), acc.equity)
        dd_pct = (peak - acc.equity) / peak * 100 if peak > 0 else 0.0
        atr_med = float(atr.iloc[-100:].median())
        riesgo_pct = calcular_riesgo_adaptativo(RISK * 100, RISK_RED * 100, dd_pct, av, atr_med)
        razon = None
        if hora < H_INI or hora >= H_FIN: razon = f"fuera_sesion h={hora}"
        elif n_dia >= MAX_TRADES_DIA: razon = f"max_trades_dia={n_dia}"
        elif pnl_dia <= -bal * MAX_LOSS_DIA_PCT / 100.0: razon = f"max_loss_dia pnl={pnl_dia:.2f}"
        elif info.spread > SPREAD_MAX_PTS: razon = f"spread_alto={info.spread}"
        elif av < float(CFG.get("backtest_params", {}).get("costes_spread", 0.16)) * 3: razon = f"atr_bajo={av:.2f}"
        elif not (zv > UZ and pv > PM): razon = f"sin_senal z={zv:.2f} p={pv:.3f}"
        elif p_mc <= PMC_MIN: razon = f"mc_bajo={p_mc:.2f}"
        if razon:
            c = sqlite3.connect(DB)
            c.execute("INSERT INTO no_trades(ts,symbol,z,p_up,p_mc,razon) VALUES(?,?,?,?,?,?)",
                      (ts, SYMBOL, zv, pv, p_mc, razon)); c.commit(); c.close()
            print(f"[{k}] FLAT {razon} mc={p_mc:.2f} dd={dd_pct:.1f}% riesgo={riesgo_pct:.2f}% pnl_dia={pnl_dia:.2f}", flush=True)
        else:
            sl_d = SLK * av
            lote_raw = (bal * riesgo_pct / 100.0) / (sl_d * 100.0)   # 1.00 precio = 100 USD/lote verificado
            step = float(info.volume_step) or 0.01
            if lote_raw < float(info.volume_min):
                print(f"[{k}] SKIP riesgo: lote calculado menor al mínimo del broker", flush=True)
                time.sleep(a.interval); continue
            lote = round(max(float(info.volume_min), min(float(info.volume_max), np.floor(lote_raw / step) * step)), 8)
            tick = mt5.symbol_info_tick(SYMBOL)
            entry, sl, tp = tick.ask, round(tick.ask - sl_d, 2), round(tick.ask + TPK * av, 2)
            r, fill = send_market(lote, sl, tp)
            if r is not None and r.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED):
                pos_sig = {"ts": ts, "lado": "BUY", "ticket": r.order, "entry": entry, "sl": sl, "tp": tp,
                           "lote": lote, "z": zv, "p_up": pv, "p_mc": p_mc, "riesgo_pct": riesgo_pct,
                           "motivo": f"FluxoV2 fill={fill}"}
                registrar_demo(ts, pos_sig, "abierta")
                print(f"[{k}] DEMO BUY ticket={r.order} lote={lote} entry={entry:.2f} sl={sl:.2f} tp={tp:.2f} "
                      f"z={zv:.2f} p={pv:.3f} mc={p_mc:.2f} dd={dd_pct:.1f}%", flush=True)
            else:
                err = r.retcode if r is not None else "None"
                print(f"[{k}] ERR order_send retcode={err} last={mt5.last_error()}", flush=True)
                c = sqlite3.connect(DB)
                c.execute("INSERT INTO no_trades(ts,symbol,z,p_up,p_mc,razon) VALUES(?,?,?,?,?,?)",
                          (ts, SYMBOL, zv, pv, p_mc, f"order_err={err}")); c.commit(); c.close()
        time.sleep(a.interval)
    mt5.shutdown()
    print("FASE 4 CICLO OK", flush=True)

if __name__ == "__main__":
    main()
