"""Fase 5 C1: publicador de senal FluxoV2 para el EA MQL5.
Calcula la senal (igual que live_demo) y escribe JSON en Common\\Files del MT5.
NUNCA envia ordenes: el EA FluxoV2_EA es el unico ejecutor.
Uso: py live_publish.py --iter 1
"""
import os, sys, json, sqlite3, time, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np
import pandas as pd
import MetaTrader5 as mt5
from dotenv import load_dotenv
from live_demo import (DB, LOGIN, PASSWORD, SERVER, SYMBOL, MT5_PATH, UZ, PM, TPK, SLK,
                       H_INI, H_FIN, MAX_TRADES_DIA, MAX_LOSS_DIA_PCT, RISK, RISK_RED,
                       DD_RED_PCT, MAGIC, MAXHOLD_VELAS, SPREAD_MAX_PTS, db_init, registrar_demo,
                       actualizar_cierre, peak_previo, flujo_live, bayes_live, monte_carlo_live)

load_dotenv()
COMMON_FILES = Path(os.getenv("MT5_COMMON_FILES",
    r"C:\Users\javie\AppData\Roaming\MetaQuotes\Terminal\Common\Files"))
SIG = COMMON_FILES / "fluxov2_signal.json"

def publicar(senal):
    SIG.parent.mkdir(parents=True, exist_ok=True)
    senal["epoch"] = int(time.time())
    tmp = SIG.with_suffix(".tmp")
    tmp.write_text(json.dumps(senal), encoding="utf-16")   # UTF-16: formato nativo que MQL5 lee por defecto
    os.replace(tmp, SIG)   # atomico: el EA nunca lee a medias

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iter", type=int, default=1)
    ap.add_argument("--interval", type=int, default=10)
    a = ap.parse_args()
    db_init()
    if not mt5.initialize(path=MT5_PATH, timeout=20000):
        print(f"ERR initialize {mt5.last_error()}", flush=True); sys.exit(1)
    if not mt5.login(int(LOGIN), password=PASSWORD, server=SERVER):
        print(f"ERR login {mt5.last_error()}", flush=True); mt5.shutdown(); sys.exit(1)
    acc = mt5.account_info()
    if acc.trade_mode != 0:
        print("ABORT no demo", flush=True); mt5.shutdown(); sys.exit(2)
    if not mt5.symbol_select(SYMBOL, True):
        print(f"ERR select {SYMBOL}", flush=True); mt5.shutdown(); sys.exit(1)
    info = mt5.symbol_info(SYMBOL)
    print(f"PUBLISH OK bal={acc.balance} eq={acc.equity}", flush=True)
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
        df_c = df.iloc[:-1].reset_index(drop=True)
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
        # memoria: detectar cierres por SL/TP del servidor
        c = sqlite3.connect(DB)
        row = c.execute("SELECT v FROM estado WHERE k='last_out_ticket'").fetchone()
        last_out = int(row[0]) if row else 0
        c.close()
        for d in sorted(outs, key=lambda x: x.ticket):
            if d.ticket <= last_out: continue
            c2 = sqlite3.connect(DB)
            fila = c2.execute("SELECT tp, sl FROM demo_trades WHERE ticket=? ORDER BY id DESC LIMIT 1",
                              (d.position_id,)).fetchone()
            c2.close()
            if fila and fila[0] is not None and fila[1] is not None:
                cierre = "tp" if abs(d.price - fila[0]) <= abs(d.price - fila[1]) else "sl"
            else:
                cierre = "cierre_ea"
            actualizar_cierre(d.position_id, float(d.profit), float(d.price), cierre)
            c = sqlite3.connect(DB)
            c.execute("INSERT OR REPLACE INTO estado(k,v) VALUES('last_out_ticket',?)", (str(d.ticket),))
            c.commit(); c.close()
            print(f"[{k}] CIERRE REG pos={d.position_id} tipo={cierre} pnl={d.profit:.2f}", flush=True)
        # recuperacion de huerfanas (proceso murio tras orden)
        poss = mt5.positions_get(symbol=SYMBOL) or []
        mias = [p for p in poss if p.magic == MAGIC]
        if mias:
            pos = mias[0]
            c2 = sqlite3.connect(DB)
            existe = c2.execute("SELECT 1 FROM demo_trades WHERE ticket=?", (pos.ticket,)).fetchone()
            c2.close()
            if not existe:
                registrar_demo(datetime.now(timezone.utc).isoformat(),
                               {"lado": "BUY", "ticket": pos.ticket, "entry": pos.price_open,
                                "sl": pos.sl, "tp": pos.tp, "lote": pos.volume, "z": 0.0,
                                "p_up": 0.0, "p_mc": 0.0, "riesgo_pct": 0.0,
                                "motivo": "RECUPERADA_HUERFANA"}, "abierta")
                print(f"[{k}] RECUPERADA huerfana ticket={pos.ticket}", flush=True)
        # decision de senal (identica a live_demo)
        peak = max(peak_previo(), acc.equity)
        dd_pct = (peak - acc.equity) / peak * 100 if peak > 0 else 0.0
        riesgo_pct = RISK * 100 if dd_pct <= DD_RED_PCT else RISK_RED * 100
        tick = mt5.symbol_info_tick(SYMBOL)
        razon = None
        if tick is None: razon = "sin_tick"
        if hora < H_INI or hora >= H_FIN: razon = f"fuera_sesion h={hora}"
        elif n_dia >= MAX_TRADES_DIA: razon = f"max_trades_dia={n_dia}"
        elif pnl_dia <= -bal * MAX_LOSS_DIA_PCT / 100.0: razon = f"max_loss_dia pnl={pnl_dia:.2f}"
        elif info.spread > SPREAD_MAX_PTS: razon = f"spread_alto={info.spread}"
        elif av < 0.16 * 3: razon = f"atr_bajo={av:.2f}"
        elif mias: razon = "posicion_abierta"
        elif not (zv > UZ and pv > PM): razon = f"sin_senal z={zv:.2f} p={pv:.3f}"
        elif p_mc <= 0.30: razon = f"mc_bajo={p_mc:.2f}"
        if razon:
            c = sqlite3.connect(DB)
            c.execute("INSERT INTO no_trades(ts,symbol,z,p_up,p_mc,razon) VALUES(?,?,?,?,?,?)",
                      (ts, SYMBOL, zv, pv, p_mc, razon)); c.commit(); c.close()
            publicar({"action": "FLAT", "symbol": SYMBOL, "price": float(tick.bid) if tick else 0.0,
                      "atr": av, "sl": 0.0, "tp": 0.0, "lot": 0.0, "z": zv, "p_up": pv,
                      "p_mc": p_mc, "magic": MAGIC, "maxhold_min": MAXHOLD_VELAS * 15,
                      "razon": razon})
            print(f"[{k}] FLAT {razon} dd={dd_pct:.1f}%", flush=True)
        else:
            sl_d = SLK * av
            lote_raw = (bal * riesgo_pct / 100.0) / (sl_d * 100.0)
            step = float(info.volume_step) or 0.01
            lote = round(max(float(info.volume_min), min(float(info.volume_max),
                     round(lote_raw / step) * step)), 2)
            publicar({"action": "BUY", "symbol": SYMBOL, "price": float(tick.ask),
                      "atr": av, "sl": round(tick.ask - sl_d, 2),
                      "tp": round(tick.ask + TPK * av, 2), "lot": lote,
                      "z": zv, "p_up": pv, "p_mc": p_mc, "magic": MAGIC,
                      "maxhold_min": MAXHOLD_VELAS * 15, "razon": "senal_BUY"})
            print(f"[{k}] SENAL PUBLICADA BUY lote={lote} sl={tick.ask-sl_d:.2f} "
                  f"tp={tick.ask+TPK*av:.2f} z={zv:.2f} p={pv:.3f} mc={p_mc:.2f}", flush=True)
        time.sleep(a.interval)
    mt5.shutdown()
    print("PUBLISH CICLO OK", flush=True)

if __name__ == "__main__":
    main()