"""Fase 2b: Monte Carlo + backtest grid sobre flux_muestra.csv.
Uso: py flux_backtest.py -> reporte_fase2b.txt (elige mejor uz/p_min por expectancy)
"""
from pathlib import Path
import numpy as np
import pandas as pd
BASE = Path(__file__).parent
DATA = BASE / "data"

def mc(df, i, n_paths=2000, horizon=20):
    win = df["px"].iloc[max(0, i-100):i+1].astype(float).values
    if len(win) < 20:
        return 0.5, 0.0
    lr = np.diff(np.log(win + 1e-12))
    mu, sigma = float(np.mean(lr)), float(np.std(lr) + 1e-9)
    atr = float(df["px"].iloc[max(0,i-14):i+1].max() - df["px"].iloc[max(0,i-14):i+1].min())
    p0 = float(df["px"].iloc[i])
    tp, sl = p0 + 1.0*atr, p0 - 0.7*atr
    paths = p0 * np.exp(np.cumsum(np.random.normal(mu, sigma, (n_paths, horizon)), axis=1))
    hit_tp = paths.max(axis=1) >= tp
    hit_sl = paths.min(axis=1) <= sl
    p_ok = float(((hit_tp) & (~hit_sl)).mean() + 0.5 * (hit_tp & hit_sl).mean())
    return p_ok, float(paths[:, -1].mean() - p0)

def backtest(df, uz, pm):
    atr = (df["px"].rolling(14).max() - df["px"].rolling(14).min()).bfill().fillna(1.0)
    trs = []
    i, n = 120, len(df)
    while i < n - 16:
        z = float(df["z"].iloc[i]); p = float(df["p_up"].iloc[i])
        lado = 1 if (z > uz and p > pm) else (-1 if (z < -uz and p < 1 - pm) else 0)
        if not lado:
            i += 1; continue
        e = float(df["px"].iloc[i]); a = float(atr.iloc[i])
        tp = e + lado*1.2*a; sl = e - lado*0.8*a; s = float(df["px"].iloc[min(i+15, n-1)]); m = "timeout"
        for j in range(i+1, min(i+16, n)):
            c = float(df["px"].iloc[j])
            if lado == 1:
                if c >= tp: s, m = tp, "TP"; break
                if c <= sl: s, m = sl, "SL"; break
            else:
                if c <= tp: s, m = tp, "TP"; break
                if c >= sl: s, m = sl, "SL"; break
            s = c
        trs.append((lado, e, s, lado*(s-e), m))
        i += 16
    return pd.DataFrame(trs, columns=["lado","entry","exit","pnl","motivo"])

def main():
    f = pd.read_csv(DATA / "flux_muestra.csv")
    mid = len(f)//2
    p_ok, exp = mc(f, mid)
    print(f"MC medio: P={p_ok:.3f} exp={exp:.2f}", flush=True)
    filas = []
    for uz in [1.0, 1.5, 2.0]:
        for pm in [0.55, 0.60]:
            tr = backtest(f, uz, pm)
            if len(tr) == 0:
                filas.append((uz, pm, 0, 0, 0, 0)); continue
            w = float((tr["pnl"] > 0).mean())
            pf = float(tr.loc[tr.pnl>0,"pnl"].sum() / (abs(tr.loc[tr.pnl<=0,"pnl"].sum()) + 1e-9))
            filas.append((uz, pm, len(tr), round(w,3), round(pf,2), round(float(tr["pnl"].mean()),2)))
    best = sorted(filas, key=lambda x: x[5], reverse=True)[0]
    txt = (f"FASE 2b MC medio P={p_ok:.3f} exp={exp:.2f}\nuz|pm|n|win|PF|exp\n" +
           "\n".join(f"{r[0]}|{r[1]}|{r[2]}|{r[3]}|{r[4]}|{r[5]}" for r in filas) +
           f"\nMEJOR expectancy: uz={best[0]} pm={best[1]} n={best[2]} win={best[3]} PF={best[4]} exp={best[5]}\n")
    print(txt, flush=True)
    (BASE / "reporte_fase2b.txt").write_text(txt, encoding="utf-8")

if __name__ == "__main__":
    main()
