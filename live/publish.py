"""Publicador FluxoV2 — módulo unificado de live trading.

Calcula la señal (flujo + Bayes + Monte Carlo) y publica JSON
para el EA ejecutor. NUNCA envía órdenes: el EA es el único executor.
Refactor de live_publish.py usando core/ y config/.

Uso: python live/publish.py --iter 1
"""
import os, sys, json, sqlite3, time, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np
import pandas as pd
from dotenv import load_dotenv

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

load_dotenv(BASE / ".env")

from config.validator import load_config, load_adaptive_config
from core.indicators import calcular_flujo, calcular_bayes, calcular_regimen, calcular_atr
from core.risk import calcular_riesgo_adaptativo

CONFIG = (load_adaptive_config(str(BASE / "config.json"), str(BASE / "config_adaptive.json"))
          if os.getenv("FLUX_ADAPTIVE", "0") == "1"
          else load_config(str(BASE / "config.json")))
DB = BASE / "trading_log.db"
COMMON_FILES = Path(os.getenv("MT5_COMMON_FILES", r"C:\Users\javie\AppData\Roaming\MetaQuotes\Terminal\Common\Files"))
SIG = COMMON_FILES / "fluxov2_signal.json"

UZ = float(CONFIG.get("estrategia_params.uz", CONFIG.get("uz", 1.0)))
PM = float(CONFIG.get("estrategia_params.pm", CONFIG.get("pm", 0.55)))
TPK = float(CONFIG.get("estrategia_params.tp_k", CONFIG.get("tp_k", 2.0)))
SLK = float(CONFIG.get("estrategia_params.sl_k", CONFIG.get("sl_k", 0.8)))
H_INI = int(CONFIG.get("sesion_params.ini_hora_utc", CONFIG.get("sesion_utc", [7, 20])[0]))
H_FIN = int(CONFIG.get("sesion_params.fin_hora_utc", CONFIG.get("sesion_utc", [7, 20])[1]))
MAX_TRADES_DIA = int(CONFIG.get("riesgo_params.max_trades_dia", CONFIG.get("max_trades_dia", 3)))
MAX_LOSS_DIA_PCT = float(CONFIG.get("riesgo_params.max_daily_loss_pct", CONFIG.get("max_daily_loss_pct", 2.0)))
RISK = float(CONFIG.get("riesgo_params.base_pct", CONFIG.get("risk_pct_por_trade", 0.5))) / 100.0
RISK_RED = float(CONFIG.get("riesgo_params.reducido_pct", CONFIG.get("risk_reducido_pct", 0.25))) / 100.0
DD_RED_PCT = float(CONFIG.get("riesgo_params.reduccion_dd_pct", 10.0))
MAGIC = int(CONFIG.get("riesgo_params.magic", CONFIG.get("magic", 20260915)))
SPREAD_MAX_PTS = int(CONFIG.get("estrategia_params.spread_max_pts", 30))


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
    c.commit(); c.close()

def peak_previo():
    c = sqlite3.connect(DB)
    row = c.execute("SELECT MAX(equity) FROM equity").fetchone()
    c.close()
    return float(row[0] or 0.0)


def publicar(senal):
    SIG.parent.mkdir(parents=True, exist_ok=True)
    senal["epoch"] = int(time.time())
    tmp = SIG.with_suffix(".tmp")
    tmp.write_text(json.dumps(senal), encoding="utf-16")
    os.replace(tmp, SIG)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iter", type=int, default=1)
    ap.add_argument("--interval", type=int, default=10)
    a = ap.parse_args()

    import MetaTrader5 as mt5
    MT5_PATH = os.getenv("MT5_PATH", CONFIG.get("live_params.mt5_path", r"D:\mt5\terminal64.exe"))
    LOGIN = int(os.getenv("MT5_LOGIN", ""))
    PASSWORD = os.getenv("MT5_PASSWORD", "")
    SERVER = os.getenv("MT5_SERVER", "Deriv-Demo")
    SYMBOL = os.getenv("MT5_SYMBOL", CONFIG.get("broker.symbol", "XAUUSD"))

    db_init()
    print("=== LIVE PUBLISH FLUXOV2 ===", flush=True)

    holder = {}
    def do_init():
        try: holder["ok"] = mt5.initialize(path=MT5_PATH, timeout=20000)
        except Exception as e: holder["exc"] = str(e)
    th = __import__("threading").Thread(target=do_init, daemon=True)
    th.start(); th.join(timeout=30)
    if not holder.get("ok"):
        print(f"INIT FAIL {holder.get('exc')} {mt5.last_error()}", flush=True); sys.exit(1)
    print("INIT OK", flush=True)

    if not mt5.login(LOGIN, password=PASSWORD, server=SERVER):
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
            print(f"[{k}] sin velas", flush=True); time.sleep(a.interval); continue
        df = pd.DataFrame(rates).iloc[:-1].reset_index(drop=True)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        flujo_df = calcular_flujo(df)
        flujo_df["exp"] = calcular_regimen(df)["exp"]
        zv, av = float(flujo_df["z"].iloc[-1]), float(flujo_df["atr"].iloc[-1]) if "atr" in flujo_df.columns else 1.0
        pv = calcular_bayes(flujo_df["Q"], flujo_df["z"])
        pv = float(pv.iloc[-1])
        from core.indicators import calcular_monte_carlo
        p_mc = calcular_monte_carlo(df["close"], flujo_df["atr"].iloc[-1])

        hora = datetime.now(timezone.utc).hour
        bal = acc.balance
        d0 = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        deals = mt5.history_deals_get(d0, d0 + timedelta(days=2)) or []
        outs = [d for d in deals if d.magic == MAGIC and d.entry == mt5.DEAL_ENTRY_OUT]
        d0ts = d0.timestamp()
        n_dia = len([d for d in deals if d.magic == MAGIC and d.entry == mt5.DEAL_ENTRY_IN and d.time >= d0ts])
        pnl_dia = sum(d.profit for d in outs if d.time >= d0ts)

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
            from live_demo import actualizar_cierre
            actualizar_cierre(d.position_id, float(d.profit), float(d.price), cierre)
            c = sqlite3.connect(DB)
            c.execute("INSERT OR REPLACE INTO estado(k,v) VALUES('last_out_ticket',?)", (str(d.ticket),))
            c.commit(); c.close()

        peak = max(peak_previo(), acc.equity)
        dd_pct = (peak - acc.equity) / peak * 100 if peak > 0 else 0.0
        atr_med = float(calcular_atr(df, 14).iloc[-100:].median())
        riesgo_pct = calcular_riesgo_adaptativo(RISK * 100, RISK_RED * 100, dd_pct, av, atr_med)
        tick = mt5.symbol_info_tick(SYMBOL)
        razon = None
        if tick is None: razon = "sin_tick"
        if hora < H_INI or hora >= H_FIN: razon = f"fuera_sesion h={hora}"
        elif n_dia >= MAX_TRADES_DIA: razon = f"max_trades_dia={n_dia}"
        elif pnl_dia <= -bal * MAX_LOSS_DIA_PCT / 100.0: razon = f"max_loss_dia pnl={pnl_dia:.2f}"
        elif info.spread > SPREAD_MAX_PTS: razon = f"spread_alto={info.spread}"
        elif av < float(CONFIG.get("estrategia_params.atr_min_mult_spread", 3)) * float(CONFIG.get("backtest_params.costes_spread", 0.16)):
            razon = f"atr_bajo={av:.2f}"
        elif not (zv > UZ and pv > PM): razon = f"sin_senal z={zv:.2f} p={pv:.3f}"
        elif p_mc <= 0.30: razon = f"mc_bajo={p_mc:.2f}"
        elif CONFIG.get("filtro_expansion", CONFIG.get("regimen.activo", False)) and not bool(flujo_df.get("exp", pd.Series([0])).iloc[-1]):
            razon = "fuera_expansion"

        if razon:
            c = sqlite3.connect(DB)
            c.execute("INSERT INTO no_trades(ts,symbol,z,p_up,p_mc,razon) VALUES(?,?,?,?,?,?)",
                      (ts, SYMBOL, zv, pv, p_mc, razon)); c.commit(); c.close()
            publicar({"action": "FLAT", "symbol": SYMBOL, "price": float(tick.bid) if tick else 0.0,
                      "atr": av, "sl": 0.0, "tp": 0.0, "lot": 0.0, "z": zv, "p_up": pv,
                      "p_mc": p_mc, "magic": MAGIC, "maxhold_min": 60*15, "razon": razon})
            print(f"[{k}] FLAT {razon} dd={dd_pct:.1f}%", flush=True)
        else:
            sl_d = SLK * av
            tick_size = float(info.trade_tick_size or info.point)
            tick_value = float(info.trade_tick_value or 0.0)
            sl_usd_lote = (sl_d / tick_size) * tick_value if tick_size > 0 and tick_value > 0 else sl_d * 100.0
            lote_raw = (bal * riesgo_pct / 100.0) / sl_usd_lote
            step = float(info.volume_step) or 0.01
            lote = max(float(info.volume_min), min(float(info.volume_max),
                     np.floor(lote_raw / step) * step))
            lote = round(lote, 8)
            publicar({"action": "BUY", "symbol": SYMBOL, "price": float(tick.ask),
                      "atr": av, "sl": round(tick.ask - sl_d, 2),
                      "tp": round(tick.ask + TPK * av, 2), "lot": lote,
                      "z": zv, "p_up": pv, "p_mc": p_mc, "magic": MAGIC,
                      "maxhold_min": 60*15, "razon": "senal_BUY"})
            msg = f"[{k}] BUY lote={lote} z={zv:.2f} p={pv:.3f} mc={p_mc:.2f}"
            print(msg, flush=True)
        time.sleep(a.interval)
    mt5.shutdown()
    print("PUBLISH CICLO OK", flush=True)


if __name__ == "__main__":
    main()
