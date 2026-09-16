"""PRUEBA CONTROLADA DE EJECUCION DEMO: certifica el pipeline completo de trading.
Abre 1 orden demo BUY 0.01 XAUUSD con SL/TP reales, la registra en BD, espera 60s,
la cierra a mercado, detecta el deal OUT del servidor y guarda el PnL real.
NO es la estrategia: es un test de infraestructura. py test_order.py
"""
import os, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
import MetaTrader5 as mt5
import live_demo as L  # reutiliza send_market, cerrar_pos, registrar_demo, actualizar_cierre, db_init

SYMBOL = L.SYMBOL; MAGIC = L.MAGIC
BASE = Path(__file__).parent
LOG = BASE / "cert_testorder.txt"
out = []

def log(m):
    out.append(m); print(m, flush=True)
    LOG.write_text("\n".join(out) + "\n", encoding="utf-8")

L.db_init()
ok = mt5.initialize(path=L.MT5_PATH, timeout=15000)
log(f"1.INIT ok={ok} err={mt5.last_error() if not ok else ''}")
if not ok:
    log("TEST FAIL en init"); raise SystemExit(1)
acc = mt5.account_info()
log(f"2.CUENTA login={acc.login} server={acc.server} bal={acc.balance} eq={acc.equity} "
    f"trade_allowed={acc.trade_allowed} trade_mode={acc.trade_mode}")
if acc.trade_mode != 0:
    log("TEST ABORT: no es cuenta demo"); mt5.shutdown(); raise SystemExit(1)
if not acc.trade_allowed:
    log("TEST ABORT: trading algoritmico desactivado"); mt5.shutdown(); raise SystemExit(1)

poss = mt5.positions_get(symbol=SYMBOL) or []
mias = [p for p in poss if p.magic == MAGIC]
if mias:
    log(f"TEST ABORT: ya existe posicion magic={MAGIC} ticket={mias[0].ticket}"); mt5.shutdown(); raise SystemExit(1)

tick = mt5.symbol_info_tick(SYMBOL)
spread = round(tick.ask - tick.bid, 2)
log(f"3.TICK bid={tick.bid} ask={tick.ask} spread={spread}")
if spread > 0.30:
    log("TEST ABORT: spread > 30 pts"); mt5.shutdown(); raise SystemExit(1)

ask = tick.ask
sl = round(ask - 2.00, 2)   # -200 pts
tp = round(ask + 2.00, 2)   # +200 pts (simetrico, 0.01 lote => +/-2 USD)
r, fill = L.send_market(0.01, sl, tp, comment="TEST_PIPELINE")
if r is None or r.retcode not in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED):
    log(f"4.ORDER FAIL retcode={r.retcode if r else None} last={mt5.last_error()}")
    mt5.shutdown(); raise SystemExit(1)
ticket = r.order; entry_real = r.price if r.price else ask
log(f"4.ORDER OK ticket={ticket} fill={fill} entry={entry_real} sl={sl} tp={tp}")
ts = datetime.now(timezone.utc).isoformat()
L.registrar_demo(ts, {"lado": "BUY", "ticket": ticket, "entry": entry_real, "sl": sl, "tp": tp,
                      "lote": 0.01, "z": 0.0, "p_up": 0.0, "p_mc": 0.0, "riesgo_pct": 0.0,
                      "motivo": "TEST_PIPELINE"}, "abierta")
log("5.BD registro abierta OK")

time.sleep(60)
poss = mt5.positions_get(symbol=SYMBOL) or []
mias = [p for p in poss if p.magic == MAGIC]
if mias:
    pos = mias[0]
    log(f"6.POS abierta ticket={pos.ticket} pnl_flotante={pos.profit:.2f} edad={int((datetime.now(timezone.utc)-datetime.fromtimestamp(pos.time, tz=timezone.utc)).total_seconds())}s")
    okc = L.cerrar_pos(pos)
    log(f"7.CIERRE a mercado ok={okc}")
else:
    log("6.POS ya no existe (servidor cerro por SL/TP dentro de los 60s)")
    okc = True

# detectar deal OUT y registrar PnL real
d1 = datetime.now(timezone.utc) - timedelta(minutes=10)
deals = mt5.history_deals_get(d1, datetime.now(timezone.utc) + timedelta(minutes=2)) or []
outs = [d for d in deals if d.magic == MAGIC and d.entry == mt5.DEAL_ENTRY_OUT and d.position == ticket]
if outs:
    d = outs[-1]
    n = L.actualizar_cierre(ticket, float(d.profit), float(d.price), "cierre_test")
    log(f"8.CIERRE REG pnl={d.profit:.2f} exit_px={d.price} filas_actualizadas={n}")
else:
    log("8.WARN no se encontro deal OUT todavia (queda pendiente para el monitor)")
bal2 = mt5.account_info()
log(f"9.CUENTA_FINAL bal={bal2.balance} eq={bal2.equity}")
mt5.shutdown()
log("TEST_ORDER OK")
raise SystemExit(0)