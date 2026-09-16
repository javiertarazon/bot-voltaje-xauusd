"""Fase 2a: indicadores FluxoVoltaic (fluido+circuito) + Bayes.
Uso: py flux_core.py  -> genera data/flux_muestra.csv + reporte_fase2a.txt
Lee ticks o M15/M5 de data/.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
BASE = Path(__file__).parent
DATA = BASE / "data"

def cargar():
    for cand in [DATA / "xauusd_M15.csv", DATA / "xauusd_M5.csv", DATA / "xauusd_ticks_30d.csv"]:
        if cand.exists():
            print(f"usando {cand}", flush=True)
            return pd.read_csv(cand), cand.name
    print("ERROR: no hay datos en data/")
    sys.exit(1)

def a_ohlc(df_raw):
    if "close" in df_raw.columns:
        return df_raw.reset_index(drop=True)
    print(f"ticks crudos: {len(df_raw)} filas. Remuestreo 30s...", flush=True)
    tcol = "time"
    try:
        if str(df_raw[tcol].iloc[0]).replace(".","",1).isdigit():
            df_raw[tcol] = pd.to_datetime(df_raw[tcol].astype(float), unit="s", utc=True)
        else:
            df_raw[tcol] = pd.to_datetime(df_raw[tcol], utc=True)
    except Exception as e:
        print(f"ERR time: {e}"); sys.exit(1)
    df_raw = df_raw.dropna(subset=[tcol]).set_index(tcol).sort_index()
    col = "bid" if "bid" in df_raw.columns else "last"
    px = df_raw[col].astype(float).resample("30s").agg(["first","max","min","last"])
    px.columns = ["open","high","low","close"]
    px = px.dropna().reset_index()
    print(f"remuestreado: {len(px)} velas 30s", flush=True)
    return px

def flujo(df):
    px = df["close"].astype(float)
    vol = df["tick_volume"].astype(float) if "tick_volume" in df.columns else pd.Series(1.0, index=df.index)
    ret = px.diff().fillna(0.0)
    atr = (px.rolling(14).max() - px.rolling(14).min()).bfill().fillna(1.0)
    vol_med = vol.rolling(50).mean().bfill().fillna(1.0) + 1e-9
    R = atr / vol_med
    I = ret / (R + 1e-9)
    C = (px.rolling(20).max() - px.rolling(20).min()).fillna(0.0)
    Q = (np.sign(ret) * vol).rolling(20).sum().fillna(0.0)
    z = ((I - I.rolling(100).mean()) / (I.rolling(100).std() + 1e-9)).fillna(0.0)
    return pd.DataFrame({"px": px, "I": I, "R": R, "C": C, "Q": Q, "z": z})

def bayes(f, lookback=50):
    # Version vectorizada rapida: verosimilitud por tanh(Q,z), posterior recursivo aproximado por EMA bayesiana
    qm = abs(f["Q"]).rolling(lookback, min_periods=1).mean() + 1e-9
    like = 0.5 + 0.3 * np.tanh(f["Q"] / qm) + 0.2 * np.tanh(f["z"] / 2.0)
    like = like.clip(0.05, 0.95)
    # Actualizacion bayesiana recursiva con decaimiento (olvido) para no saturar en 0/1
    p = np.empty(len(f)); p[0] = 0.5
    lam = 0.98  # olvido: prior efectivo = lam*p_prev + (1-lam)*0.5
    for i in range(1, len(f)):
        prev = lam * p[i-1] + (1 - lam) * 0.5
        li = float(like.iloc[i])
        p[i] = li * prev / (li * prev + (1 - li) * (1 - prev) + 1e-12)
    return pd.Series(p, index=f.index)

def main():
    raw, nombre = cargar()
    df = a_ohlc(raw)
    f = flujo(df)
    if len(f) > 60000:
        f = f.tail(60000).reset_index(drop=True)
        print(f"muestra tail 60k", flush=True)
    print("Bayes...", flush=True)
    p = bayes(f)
    f["p_up"] = p
    out = DATA / "flux_muestra.csv"
    f.tail(5000).to_csv(out, index=False)
    rep = (f"FASE 2a OK datos={nombre} n={len(f)}\n"
           f"z media={f['z'].mean():.3f} std={f['z'].std():.3f}\n"
           f"p_up media={p.mean():.3f} p_up ultimo={float(p.iloc[-1]):.3f}\n"
           f"Q ultimo={float(f['Q'].iloc[-1]):.1f} I ultimo={float(f['I'].iloc[-1]):.3f}\n"
           f"px ultimo={float(f['px'].iloc[-1]):.2f}\n"
           f"muestra -> {out}\n")
    print(rep, flush=True)
    (BASE / "reporte_fase2a.txt").write_text(rep, encoding="utf-8")

if __name__ == "__main__":
    main()
