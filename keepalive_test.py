"""EXPERIMENTO LIMITACION IPC: proceso unico con latido cada 30s durante 12 min.
Si sobrevive, la IP C no se cuelga por inactividad<30s y podemos usar proceso largo. py keepalive_test.py"""
import time
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
import MetaTrader5 as mt5
LOG = Path(__file__).parent / "cert_keepalive.txt"
out = []

def log(m):
    out.append(f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} {m}")
    print(out[-1], flush=True)
    LOG.write_text("\n".join(out) + "\n", encoding="utf-8")

ok = mt5.initialize(path=r"D:\mt5\terminal64.exe", timeout=15000)
log(f"init={ok} err={mt5.last_error() if not ok else ''}")
if ok:
    log("INICIO latido cada 30s x 24 iteraciones (12 min)")
    for i in range(24):
        time.sleep(30)
        t = mt5.symbol_info_tick("XAUUSD")
        log(f"iter={i} tick={'OK bid=' + str(t.bid) if t else 'FAIL ' + str(mt5.last_error())}")
    mt5.shutdown()
    log("KEEPALIVE_TEST_OK 12min sin cuelgue")
else:
    log("KEEPALIVE_TEST_FAIL_INIT")