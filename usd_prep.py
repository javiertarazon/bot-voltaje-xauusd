"""Backtest USD parte A: arrays flujo. Uso: py usd_prep.py"""
from pathlib import Path
import numpy as np
import pandas as pd
BASE = Path(__file__).parent
DATA = BASE / "data"
def main():
    df = pd.read_csv(DATA / "xauusd_M15.csv")
    df["time"] = pd.to_datetime(df["time"], utc=True)
    d = df[(df["time"] >= "2025-01-01") & (df["time"] < "2026-01-01")].reset_index(drop=True)
    for c in ["open", "high", "low", "close", "tick_volume"]:
        d[c] = d[c].astype(float)
    px, vol = d["close"], d["tick_volume"]
    ret = px.diff().fillna(0.0)
    prev = px.shift(1)
    tr = pd.concat([d.high - d.low, (d.high - prev).abs(), (d.low - prev).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().bfill()
    vol_med = vol.rolling(50).mean().bfill().fillna(1.0) + 1e-9
    R = atr / vol_med
    I = ret / (R + 1e-9)
    Q = (np.sign(ret) * vol).rolling(20).sum().fillna(0.0)
    z = ((I - I.rolling(100).mean()) / (I.rolling(100).std() + 1e-9)).fillna(0.0)
    qm = abs(Q).rolling(50, min_periods=1).mean() + 1e-9
    like = (0.5 + 0.3 * np.tanh(Q / qm) + 0.2 * np.tanh(z / 2.0)).clip(0.05, 0.95)
    p = np.empty(len(d)); p[0] = 0.5
    lv = like.values
    for i in range(1, len(d)):
        pr = 0.98 * p[i-1] + 0.02 * 0.5
        li = float(lv[i])
        p[i] = li * pr / (li * pr + (1 - li) * (1 - pr) + 1e-12)
    np.savez_compressed(DATA / "usd_2025.npz", hi=d.high.values, lo=d.low.values,
                        cl=d.close.values, z=z.values, p=p, atr=atr.values,
                        t=d.time.astype(str).values, h=d.time.dt.hour.values)
    print(f"USD PREP OK n={len(d)}", flush=True)
if __name__ == "__main__":
    main()
