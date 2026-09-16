"""V3b: V2 intacto + unico filtro regimen ATR14>ATR100 (on/off).
Uso: py backtest_v3b.py -> reporte_backtest_v3b.txt + data/trades_v3b.csv
Sin trailing, sin horas, sin half-size. TP=2.0 SL=0.8 hold=60 sesion 7-20UTC max3/dia.
"""
from pathlib import Path
import numpy as np
import pandas as pd
BASE = Path(__file__).parent
DATA = BASE / "data"
SPREAD = 0.16
UZ, PM, TPK, SLK, MH = 1.0, 0.55, 2.0, 0.8, 60

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
    atr100 = atr.rolling(100).mean().bfill()
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
    hi, lo, cl = d["high"].values, d["low"].values, d["close"].values
    tm = d["time"]
    zv, pv, av, a100 = z.values, p, atr.values, atr100.values
    horas = tm.dt.hour.values
    n = len(d)
    trs = []
    conteo = {}
    i = 120
    on = off = 0
    while i < n - 2:
        h = int(horas[i])
        if h < 7 or h > 20:
            i += 1; continue
        key = str(tm.iloc[i].date())
        if conteo.get(key, 0) >= 3:
            i += 1; continue
        # UNICO FILTRO NUEVO: regimen expansion
        if not (float(av[i]) > float(a100[i])):
            off += 1
            i += 1; continue
        on += 1
        if not (zv[i] > UZ and pv[i] > PM):
            i += 1; continue
        e = float(cl[i]); a = float(av[i])
        if a < SPREAD * 3:
            i += 1; continue
        tp = e + TPK * a; sl = e - SLK * a
        s, m, jo = float(cl[min(i+MH, n-1)]), "timeout", min(i+MH, n-1)
        for j in range(i+1, min(i+MH+1, n)):
            hh, ll, cc = float(hi[j]), float(lo[j]), float(cl[j])
            btp, bsl = hh >= tp, ll <= sl
            if btp and bsl: s, m, jo = sl, "SL_amb", j; break
            if bsl: s, m, jo = sl, "SL", j; break
            if btp: s, m, jo = tp, "TP", j; break
            s, jo = cc, j
        trs.append((tm.iloc[i], tm.iloc[jo], e, s, (s-e)-SPREAD, m, jo-i))
        conteo[key] = conteo.get(key, 0) + 1
        i = jo + 1
    T = pd.DataFrame(trs, columns=["t_in", "t_out", "entry", "exit", "pnl", "motivo", "bars"])
    T.to_csv(DATA / "trades_v3b.csv", index=False)
    T["t_out"] = pd.to_datetime(T["t_out"], utc=True)
    T = T.sort_values("t_out").reset_index(drop=True)
    r = T["pnl"].values
    w = float((r > 0).mean())
    gp = r[r > 0].sum(); gl = abs(r[r <= 0].sum())
    pf = float(gp / (gl + 1e-9))
    eq = np.cumsum(r); pk = np.maximum.accumulate(eq); dd = pk - eq
    rep = [f"=== V3b solo filtro ATR14>ATR100 (velas on={on} off={off}) ===",
           f"trades={len(T)} win={w:.1%} PF={pf:.2f} exp={r.mean():+.3f} total={r.sum():+.1f} dd={dd.max():.1f}",
           f"TP={(T['motivo']=='TP').sum()} SL={(T['motivo'].isin(['SL','SL_amb'])).sum()} timeout={(T['motivo']=='timeout').sum()}",
           "--- MENSUAL ---"]
    T["mes"] = T["t_out"].dt.strftime("%Y-%m")
    for mes, gg in T.groupby("mes")["pnl"].agg(["sum", "count", "mean"]).iterrows():
        rep.append(f"  {mes}: {gg['sum']:+.1f} | n={int(gg['count'])} | exp={gg['mean']:+.2f}")
    rep.append("--- VS V2 (525 PF1.29 +461.2 dd85.4) ---")
    rep.append(f"V3b: n={len(T)} PF={pf:.2f} total={r.sum():+.1f} dd={dd.max():.1f}")
    txt = "\n".join(rep)
    print(txt, flush=True)
    (BASE / "reporte_backtest_v3b.txt").write_text(txt, encoding="utf-8")

if __name__ == "__main__":
    main()
