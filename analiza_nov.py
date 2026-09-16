"""Analisis Nov-2025 v2 (trades_opt sin z; recalcula contexto). Uso: py analiza_nov.py
"""
from pathlib import Path
import numpy as np
import pandas as pd
BASE = Path(__file__).parent
DATA = BASE / "data"

def main():
    T = pd.read_csv(DATA / "trades_opt.csv")
    T["t_in"] = pd.to_datetime(T["t_in"], utc=True)
    T["t_out"] = pd.to_datetime(T["t_out"], utc=True)
    T["mes"] = T["t_in"].dt.to_period("M").astype(str)
    nov = T[T["mes"] == "2025-11"].copy()
    resto = T[T["mes"] != "2025-11"].copy()
    nov = T[T["mes"] == "2025-11"].copy()
    resto = T[T["mes"] != "2025-11"].copy()
    px = pd.read_csv(DATA / "xauusd_M15.csv")
    px["time"] = pd.to_datetime(px["time"], utc=True)
    pn = px[(px["time"] >= "2025-11-01") & (px["time"] < "2025-12-01")].reset_index(drop=True)
    p0, p1 = float(pn["close"].iloc[0]), float(pn["close"].iloc[-1])
    mx, mn = float(pn["high"].max()), float(pn["low"].min())
    dia = pn.set_index("time")["close"].resample("D").agg(["first", "last"])
    dia["chg"] = dia["last"] - dia["first"]
    dias_up = int((dia["chg"] > 0).sum())
    upm15 = float((pn["close"].values[1:] > pn["close"].values[:-1]).mean() * 100)
    prev = pn["close"].shift(1)
    tr = pd.concat([pn.high - pn.low, (pn.high - prev).abs(), (pn.low - prev).abs()], axis=1).max(axis=1)
    atr_nov = float(tr.rolling(14).mean().mean())
    prev2 = px["close"].shift(1)
    tr2 = pd.concat([px.high - px.low, (px.high - prev2).abs(), (px.low - prev2).abs()], axis=1).max(axis=1)
    atr_all = float(tr2.rolling(14).mean().mean())
    nov["hora"] = nov["t_in"].dt.hour
    resto["hora"] = resto["t_in"].dt.hour
    rep = []
    rep.append("=== ANALISIS NOV-2025 (mejor mes +163.0 pts) ===")
    pf_n = nov.loc[nov.pnl > 0, "pnl"].sum() / (abs(nov.loc[nov.pnl <= 0, "pnl"].sum()) + 1e-9)
    rep.append(f"nov: n={len(nov)} win={(nov['pnl']>0).mean():.1%} PF={pf_n:.2f} exp={nov['pnl'].mean():+.2f}")
    rep.append(f"resto: n={len(resto)} win={(resto['pnl']>0).mean():.1%} exp={resto['pnl'].mean():+.2f}")
    rep.append(f"PRECIO NOV: open={p0:.2f} close={p1:.2f} cambio={p1-p0:+.1f} max={mx:.2f} min={mn:.2f} rango={mx-mn:.1f}")
    rep.append(f"dias Up {dias_up}/{len(dia)} M15 Up {upm15:.1f}% ATRnov={atr_nov:.2f} vs ATRanual={atr_all:.2f}")
    rep.append(f"HOLD nov={nov['bars'].mean():.1f} vs resto={resto['bars'].mean():.1f}")
    rep.append(f"TP-rate nov={(nov['motivo']=='TP').mean():.1%} vs resto={(resto['motivo']=='TP').mean():.1%}")
    rep.append("HORA UTC nov (n|pnl|exp):")
    for h, rr in nov.groupby("hora")["pnl"].agg(["count", "sum", "mean"]).sort_index().iterrows():
        rep.append(f"  {int(h):02d}h: n={int(rr['count'])} pnl={rr['sum']:+.1f} exp={rr['mean']:+.2f}")
    rep.append("HORA resto exp: " + ", ".join(f"{int(h):02d}h:{v:+.1f}" for h, v in resto.groupby("hora")["pnl"].mean().sort_index().items()))
    rep.append("DIA SEMANA nov:")
    for dd, rr in nov.groupby(nov["t_in"].dt.day_name())["pnl"].agg(["count", "sum", "mean"]).iterrows():
        rep.append(f"  {dd}: n={int(rr['count'])} pnl={rr['sum']:+.1f} exp={rr['mean']:+.2f}")
    rep.append("TOP 5 nov:")
    for _, r_ in nov.nlargest(5, "pnl").iterrows():
        rep.append(f"  {r_['t_in']} hold={int(r_['bars'])} {r_['pnl']:+.1f} {r_['motivo']}")
    rep.append("PEORES 3 nov:")
    for _, r_ in nov.nsmallest(3, "pnl").iterrows():
        rep.append(f"  {r_['t_in']} hold={int(r_['bars'])} {r_['pnl']:+.1f} {r_['motivo']}")
    rep.append("--- REGLAS FLUXOV3 PARA REPLICAR ---")
    rep.append("1. Full-size solo si ATR14>ATR100 y dia previo Up; si no half/FLAT.")
    rep.append("2. Operar solo horas calientes tabla; fuera FLAT.")
    rep.append("3. Trailing a breakeven en +1.0*ATR.")
    rep.append("4. Tras 2 TP/dia, max 1 mas.")
    txt = "\n".join(rep)
    print(txt, flush=True)
    (BASE / "reporte_nov2025.txt").write_text(txt, encoding="utf-8")

if __name__ == "__main__":
    main()
