"""Backtest 2025 XAUUSD M15 - FluxoVoltaic uz=1.0 pm=0.55.
Uso: py backtest_2025.py
Lee data/xauusd_M15.csv, filtra 2025, TP=1.2*ATR SL=0.8*ATR, spread 0.16.
Genera: reporte_backtest_2025.txt + data/trades_2025.csv + data/equity_2025.csv
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
BASE = Path(__file__).parent
DATA = BASE / "data"
UZ, PM = 1.0, 0.55
SPREAD = 0.16
ATR_P, TP_K, SL_K = 14, 1.2, 0.8

def main():
    csv = DATA / "xauusd_M15.csv"
    if not csv.exists():
        print("ERROR: falta data/xauusd_M15.csv"); sys.exit(1)
    df = pd.read_csv(csv)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    d25 = df[(df["time"] >= "2025-01-01") & (df["time"] < "2026-01-01")].reset_index(drop=True)
    print(f"velas 2025: {len(d25)} de {len(df)} ({d25['time'].iloc[0]} -> {d25['time'].iloc[-1]})", flush=True)
    if len(d25) < 500:
        print("ERROR: pocos datos 2025"); sys.exit(1)
    for c in ["open", "high", "low", "close", "tick_volume"]:
        d25[c] = d25[c].astype(float)
    # --- indicadores flujo ---
    px, vol = d25["close"], d25["tick_volume"]
    ret = px.diff().fillna(0.0)
    prev_close = px.shift(1)
    tr = pd.concat([d25["high"] - d25["low"], (d25["high"] - prev_close).abs(),
                    (d25["low"] - prev_close).abs()], axis=1).max(axis=1)
    atr = tr.rolling(ATR_P).mean().bfill()
    vol_med = vol.rolling(50).mean().bfill().fillna(1.0) + 1e-9
    R = atr / vol_med
    I = ret / (R + 1e-9)
    Q = (np.sign(ret) * vol).rolling(20).sum().fillna(0.0)
    z = ((I - I.rolling(100).mean()) / (I.rolling(100).std() + 1e-9)).fillna(0.0)
    qm = abs(Q).rolling(50, min_periods=1).mean() + 1e-9
    like = (0.5 + 0.3 * np.tanh(Q / qm) + 0.2 * np.tanh(z / 2.0)).clip(0.05, 0.95)
    p = np.empty(len(d25)); p[0] = 0.5; lam = 0.98
    lv = like.values
    for i in range(1, len(d25)):
        prev = lam * p[i-1] + (1 - lam) * 0.5
        li = float(lv[i])
        p[i] = li * prev / (li * prev + (1 - li) * (1 - prev) + 1e-12)
    zv, pv, av = z.values, p, atr.values
    hi, lo, cl, tm = d25["high"].values, d25["low"].values, d25["close"].values, d25["time"]
    # --- backtest con high/low real + spread ---
    trs = []
    i, n = 120, len(d25)
    while i < n - 2:
        lado = 0
        if zv[i] > UZ and pv[i] > PM: lado = 1
        elif zv[i] < -UZ and pv[i] < 1 - PM: lado = -1
        if not lado:
            i += 1; continue
        e = float(cl[i]); a = float(av[i])
        tp = e + lado * TP_K * a; sl = e - lado * SL_K * a
        s, m, j_out = float(cl[min(i+60, n-1)]), "timeout", min(i+60, n-1)
        for j in range(i+1, min(i+61, n)):
            h, l = float(hi[j]), float(lo[j])
            if lado == 1:
                t_tp = h >= tp; t_sl = l <= sl
                if t_tp and t_sl: s, m, j_out = sl, "SL_amb", j; break
                if t_sl: s, m, j_out = sl, "SL", j; break
                if t_tp: s, m, j_out = tp, "TP", j; break
            else:
                t_tp = l <= tp; t_sl = h >= sl
                if t_tp and t_sl: s, m, j_out = sl, "SL_amb", j; break
                if t_sl: s, m, j_out = sl, "SL", j; break
                if t_tp: s, m, j_out = tp, "TP", j; break
            s, j_out = float(cl[j]), j
        pnl = lado * (s - e) - SPREAD
        trs.append((tm.iloc[i], tm.iloc[j_out], lado, e, s, tp, sl, pnl, m,
                    float(zv[i]), float(pv[i]), j_out - i))
        i = j_out + 1
    cols = ["t_in", "t_out", "lado", "entry", "exit", "tp", "sl", "pnl_pts", "motivo", "z", "p_up", "bars"]
    T = pd.DataFrame(trs, columns=cols)
    T.to_csv(DATA / "trades_2025.csv", index=False)
    if len(T) == 0:
        print("SIN TRADES en 2025"); sys.exit(1)
    T["eq"] = T["pnl_pts"].cumsum()
    T[["t_out", "eq"]].to_csv(DATA / "equity_2025.csv", index=False)
    # --- metricas ---
    nT = len(T); wins = (T["pnl_pts"] > 0).sum(); winr = wins / nT
    gp = T.loc[T.pnl_pts > 0, "pnl_pts"].sum(); gl = abs(T.loc[T.pnl_pts <= 0, "pnl_pts"].sum())
    pf = gp / (gl + 1e-9); exp = T["pnl_pts"].mean(); tot = T["pnl_pts"].sum()
    eq = T["eq"].values; dd = float((np.maximum.accumulate(eq) - eq).max())
    ret_s = T["pnl_pts"].values; sharpe = float(ret_s.mean() / (ret_s.std() + 1e-9) * np.sqrt(nT))
    L = T[T.lado == 1]; S = T[T.lado == -1]
    mnt = T.groupby(pd.to_datetime(T["t_out"]).dt.to_period("M"))["pnl_pts"].agg(["sum", "count"])
    lot = 0.01
    usd_por_punto = 1.0  # 0.01 lotes XAUUSD ~= 1 USD por 1.00 de precio
    rep = []
    rep.append("=== BACKTEST 2025 XAUUSD M15 FluxoVoltaic (uz=1.0 pm=0.55) ===")
    rep.append(f"velas={len(d25)} {d25['time'].iloc[0]} -> {d25['time'].iloc[-1]}")
    rep.append(f"coste spread={SPREAD} TP={TP_K}*ATR SL={SL_K}*ATR maxhold=60 velas")
    rep.append(f"TRADES={nT} wins={wins} WINRATE={winr:.1%} PF={pf:.2f}")
    rep.append(f"EXPECTANCY={exp:.2f} pts/trade TOTAL={tot:.2f} pts (~{tot*usd_por_punto:.0f} USD @0.01 lotes)")
    rep.append(f"MAX_DRAWDOWN={dd:.2f} pts SHARPE*={sharpe:.2f} (*anualizado por trades)")
    rep.append(f"AVG_WIN={T.loc[T.pnl_pts>0,'pnl_pts'].mean():.2f} AVG_LOSS={T.loc[T.pnl_pts<=0,'pnl_pts'].mean():.2f}")
    rep.append(f"LONG n={len(L)} win={(L['pnl_pts']>0).mean():.1%} pnl={L['pnl_pts'].sum():.1f} | SHORT n={len(S)} win={(S['pnl_pts']>0).mean():.1%} pnl={S['pnl_pts'].sum():.1f}")
    rep.append(f"HOLD medio={T['bars'].mean():.1f} velas M15")
    rep.append("MOTIVOS: " + str(T["motivo"].value_counts().to_dict()))
    rep.append("--- MENSUAL (pts | n) ---")
    for per, r in mnt.iterrows():
        rep.append(f"  {per}: {r['sum']:+.1f} pts | {int(r['count'])} trades")
    rep.append(f"archivos: data/trades_2025.csv ({nT}) data/equity_2025.csv")
    txt = "\n".join(rep)
    print(txt, flush=True)
    (BASE / "reporte_backtest_2025.txt").write_text(txt, encoding="utf-8")

if __name__ == "__main__":
    main()
