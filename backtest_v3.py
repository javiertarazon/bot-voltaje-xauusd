"""FluxoV3: LONG + regimen impulso + horas calientes + trailing BE + cap diario.
Uso: py backtest_v3.py -> reporte_backtest_v3.txt + data/trades_v3.csv
Filtros nov: ATR14>ATR100*1.2 + dia previo Up (full) / si no half (0.5x pnl);
horas OK {7,12,13,15,16,19}; prohibidas {8,11,14}; trailing SL a BE en +1.0*ATR;
tras 2 TP/dia max 1 mas; si dia va -0.5*ATR bajo apertura -> FLAT resto dia.
"""
from pathlib import Path
import numpy as np
import pandas as pd
BASE = Path(__file__).parent
DATA = BASE / "data"
SPREAD = 0.16
UZ, PM, TPK, SLK, MH = 1.0, 0.55, 2.0, 0.8, 60
HORAS_OK = {7, 12, 13, 15, 16, 19}
HORAS_OFF = {8, 11, 14}

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
    # momentum diario: cierre dia previo vs apertura
    fecha = d["time"].dt.date.values
    dias = pd.DataFrame({"f": fecha, "cl": px.values, "op": d["open"].values})
    g = dias.groupby("f").agg(op0=("op", "first"), cl1=("cl", "last"))
    g["up"] = g["cl1"] > g["op0"]
    up_prev = g["up"].shift(1).fillna(False)
    mapa_up = dict(zip([str(k) for k in g.index], up_prev.values))
    # apertura del dia para filtro intradia -0.5*ATR
    mapa_op = dict(zip([str(k) for k in g.index], g["op0"].values))
    hi, lo, cl = d["high"].values, d["low"].values, d["close"].values
    tm = d["time"]
    zv, pv, av, a100 = z.values, p, atr.values, atr100.values
    horas = tm.dt.hour.values
    n = len(d)
    trs = []
    tp_dia = {}
    i = 120
    while i < n - 2:
        dia_k = str(fecha[i])
        h = int(horas[i])
        if h in HORAS_OFF or h not in HORAS_OK:
            i += 1; continue
        if tp_dia.get(dia_k, 0) >= 3:
            i += 1; continue
        if not (zv[i] > UZ and pv[i] > PM):
            i += 1; continue
        a = float(av[i])
        if a < SPREAD * 3:
            i += 1; continue
        # filtro intradia: si precio cae -0.5*ATR bajo apertura -> FLAT
        if float(cl[i]) < mapa_op[dia_k] - 0.5 * a:
            i += 1; continue
        impulso = (a > float(a100[i]) * 1.2) and bool(mapa_up.get(dia_k, False))
        size = 1.0 if impulso else 0.5
        e = float(cl[i])
        tp = e + TPK * a; sl = e - SLK * a
        be = e + 1.0 * a
        sl_act = sl
        s, m, jo = float(cl[min(i+MH, n-1)]), "timeout", min(i+MH, n-1)
        tp_flag = False
        for j in range(i+1, min(i+MH+1, n)):
            hh, ll, cc = float(hi[j]), float(lo[j]), float(cl[j])
            if not tp_flag and hh >= be:
                sl_act = e + SPREAD  # BE + spread para no perder por coste
                tp_flag = True
            btp, bsl = hh >= tp, ll <= sl_act
            if btp and bsl:
                s, m, jo = sl_act, "SL_amb", j; break
            if bsl:
                s, m, jo = sl_act, ("BE" if tp_flag else "SL"), j; break
            if btp:
                s, m, jo = tp, "TP", j; break
            s, jo = cc, j
        pnl = ((s - e) - SPREAD) * size
        trs.append((tm.iloc[i], tm.iloc[jo], e, s, pnl, m, jo-i, size, int(impulso)))
        if m == "TP":
            tp_dia[dia_k] = tp_dia.get(dia_k, 0) + 1
        i = jo + 1
    cols = ["t_in", "t_out", "entry", "exit", "pnl", "motivo", "bars", "size", "impulso"]
    T = pd.DataFrame(trs, columns=cols)
    T.to_csv(DATA / "trades_v3.csv", index=False)
    T["t_out"] = pd.to_datetime(T["t_out"], utc=True)
    T = T.sort_values("t_out").reset_index(drop=True)
    r = T["pnl"].values
    nn = len(T)
    w = float((r > 0).mean())
    gp = r[r > 0].sum(); gl = abs(r[r <= 0].sum())
    pf = float(gp / (gl + 1e-9))
    eq = np.cumsum(r); pk = np.maximum.accumulate(eq); dd = pk - eq
    rep = []
    rep.append("=== BACKTEST 2025 FLUXOV3 (filtros nov) ===")
    rep.append(f"trades={nn} win={w:.1%} PF={pf:.2f} exp={r.mean():+.3f} total={r.sum():+.1f} dd={dd.max():.1f}")
    rep.append(f"TP={(T['motivo']=='TP').sum()} BE={(T['motivo'].isin(['BE','BE_amb'])).sum()} SL={(T['motivo'].isin(['SL','SL_amb'])).sum()} timeout={(T['motivo']=='timeout').sum()}")
    rep.append(f"full-size n={int(T['impulso'].sum())} pnl={T.loc[T.impulso==1,'pnl'].sum():+.1f} | half n={int((T['impulso']==0).sum())} pnl={T.loc[T.impulso==0,'pnl'].sum():+.1f}")
    rep.append("--- MENSUAL ---")
    T["mes"] = T["t_out"].dt.strftime("%Y-%m")
    for mes, gg in T.groupby("mes")["pnl"].agg(["sum", "count", "mean"]).iterrows():
        rep.append(f"  {mes}: {gg['sum']:+.1f} | n={int(gg['count'])} | exp={gg['mean']:+.2f}")
    rep.append("--- VS V2 (525 trades PF1.29 +461.2 dd85.4) ---")
    rep.append(f"V3 mejora trades {nn} vs 525, PF {pf:.2f} vs 1.29, total {r.sum():+.1f} vs +461.2, dd {dd.max():.1f} vs 85.4")
    txt = "\n".join(rep)
    print(txt, flush=True)
    (BASE / "reporte_backtest_v3.txt").write_text(txt, encoding="utf-8")

if __name__ == "__main__":
    main()
