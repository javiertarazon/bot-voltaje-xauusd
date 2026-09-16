"""Fase 1: descarga historicos XAUUSD (M1/M5/M15 + ticks) a data/.
Uso: python download_history.py
Requiere .env valido y Fase 0 OK.
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: falta python-dotenv. pip install -r requirements.txt")
    sys.exit(2)

load_dotenv()
import json

BASE = Path(__file__).parent
CFG = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
DATA = BASE / CFG.get("data_dir", "data")
DATA.mkdir(exist_ok=True)

LOGIN = os.getenv("MT5_LOGIN", "")
PASSWORD = os.getenv("MT5_PASSWORD", "")
SERVER = os.getenv("MT5_SERVER", "")
SYMBOL = os.getenv("MT5_SYMBOL", CFG.get("symbol", "XAUUSD"))
MT5_PATH = os.getenv("MT5_PATH", r"D:\mt5\terminal64.exe")

try:
    import MetaTrader5 as mt5
    import pandas as pd
except ImportError as e:
    print(f"ERROR import: {e}. pip install -r requirements.txt")
    sys.exit(2)


def main():
    TF_MAP = {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15}
    print("=== FASE 1 download_history ===", flush=True)
    inicio = datetime.strptime(CFG["fecha_inicio_historia"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    fin = datetime.now(timezone.utc)
    print(f"Symbol={SYMBOL} desde={inicio.date()} hasta={fin.date()} path={MT5_PATH}", flush=True)

    if MT5_PATH and os.path.exists(MT5_PATH):
        ok = mt5.initialize(path=MT5_PATH, timeout=15000)
    else:
        ok = mt5.initialize(timeout=15000)
    if not ok:
        print(f"ERROR initialize: {mt5.last_error()}", flush=True)
        sys.exit(1)
    if not mt5.login(int(LOGIN), password=PASSWORD, server=SERVER):
        for srv in ["Deriv-Demo", "DerivSVG-Server", "Deriv-Server"]:
            print(f"Reintentando login en {srv} ...", flush=True)
            if mt5.login(int(LOGIN), password=PASSWORD, server=srv):
                print(f"Login OK server={srv}", flush=True)
                break
        else:
            print(f"ERROR login: {mt5.last_error()}", flush=True)
            mt5.shutdown()
            sys.exit(1)
    else:
        print(f"Login OK server={SERVER}", flush=True)

    mt5.symbol_select(SYMBOL, True)
    resumen = []
    for tf_name, tf in TF_MAP.items():
        print(f"Descargando {SYMBOL} {tf_name} ...", flush=True)
        rates = mt5.copy_rates_range(SYMBOL, tf, inicio, fin)
        if rates is None or len(rates) == 0:
            print(f"  AVISO: sin datos {tf_name}: {mt5.last_error()}", flush=True)
            continue
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        ruta = DATA / f"xauusd_{tf_name}.csv"
        df.to_csv(ruta, index=False)
        print(f"  OK {tf_name}: {len(df)} velas {df['time'].iloc[0]} -> {df['time'].iloc[-1]} guardado en {ruta}", flush=True)
        print(f"  Muestra:\n{df[['time','open','high','low','close','tick_volume']].head(3).to_string(index=False)}", flush=True)
        resumen.append((tf_name, len(df), str(ruta)))

    print("Descargando ticks ultimos 30 dias ...", flush=True)
    desde_ticks = fin - timedelta(days=30)
    ticks = mt5.copy_ticks_range(SYMBOL, desde_ticks, fin, mt5.COPY_TICKS_ALL)
    if ticks is not None and len(ticks) > 0:
        tdf = pd.DataFrame(ticks)
        ruta_t = DATA / "xauusd_ticks_30d.csv"
        if len(tdf) > 500000:
            tdf = tdf.tail(500000)
            print(f"  Recorte a ultimas 500k filas de {len(ticks)} ticks", flush=True)
        tdf.to_csv(ruta_t, index=False)
        print(f"  OK ticks: {len(tdf)} filas guardadas en {ruta_t}", flush=True)
        resumen.append(("TICKS", len(tdf), str(ruta_t)))
    else:
        print(f"  AVISO ticks: {mt5.last_error()}", flush=True)

    mt5.shutdown()
    print("=== RESUMEN FASE 1 ===", flush=True)
    for r in resumen:
        print(f"  {r[0]}: {r[1]} filas -> {r[2]}", flush=True)
    if not resumen:
        print("ERROR: no se descargo nada. Verifica simbolo/servidor.", flush=True)
        sys.exit(1)
    print("FASE 1 OK.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
