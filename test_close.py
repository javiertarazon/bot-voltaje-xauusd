"""RECUPERACION: cierra la posicion TEST abierta y registra su PnL en BD. py test_close.py"""
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
import MetaTrader5 as mt5
import live_demo as L

BASE = Path(__file__).parent
LOG = BASE / "cert_testclose.txt"
out = []

def log(m):
    out.append(m); print(m, flush=True)
    LOG.write_text("\n".join(out) + "\n", encoding="utf-8")

ok = mt5.initialize(path=L.MT5_PATH, timeout=15000)
log(f"1.INIT ok={ok}")
if not ok:
    raise SystemExit(1)
poss = mt5.positions_get(symbol=L.SYMBOL) or []
mias = [p for p in poss if p.magic == L.MAGIC]
if not mias:
    log("2.SIN_POS abierta (el servidor la cerro por SL/TP)")
    ticket = None
else:
    pos = mias[0]
    ticket = pos.ticket
    log(f"2.POS ticket={pos.ticket} vol={pos.volume} pnl_flot={pos.profit:.2f}")
    okc = L.cerrar_pos(pos)
    log(f"3.CIERRE ok={okc}")
    time.sleep(2)
d1 = datetime.now(timezone.utc) - timedelta(hours=2)
deals = mt5.history_deals_get(d1, datetime.now(timezone.utc) + timedelta(minutes=2)) or []
ins = [d for d in deals if d.magic == L.MAGIC and d.entry == mt5.DEAL_ENTRY_IN]
outs = [d for d in deals if d.magic == L.MAGIC and d.entry == mt5.DEAL_ENTRY_OUT]
log(f"4.DEALS in={len(ins)} out={len(outs)}")
if outs:
    for d in sorted(outs, key=lambda x: x.ticket):
        n = L.actualizar_cierre(d.position_id, float(d.profit), float(d.price), "cierre_test")
        log(f"5.OUT ticket={d.ticket} pos={d.position_id} pnl={d.profit:.2f} px={d.price} filas={n}")
else:
    log("5.WARN sin deal OUT")
acc = mt5.account_info()
log(f"6.FINAL bal={acc.balance} eq={acc.equity}")
mt5.shutdown()
log("TEST_CLOSE OK")
raise SystemExit(0)