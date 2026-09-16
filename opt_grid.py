"""OPT 2025 parte B: grid sobre npz. Uso: py opt_grid.py"""
import itertools
from pathlib import Path
import numpy as np
import pandas as pd
BASE = Path(__file__).parent
DATA = BASE / "data"
SPREAD = 0.16

def correr(hi, lo, cl, tm, zv, pv, av, ses, ex, uz, pm, tpk, slk, mh, fe):
    n = len(cl)
    trs = []
    dia = pd.to_datetime(tm).date
    conteo = {}
    i = 120
    while i < n - 2:
        k = str(dia[i])
        if conteo.get(k, 0) >= 3:
            i += 1; continue
        if not ses[i]:
            i += 1; continue
        if fe and not ex[i]:
            i += 1; continue
        if not (zv[i] > uz and pv[i] > pm):
            i += 1; continue
        e = float(cl[i]); a = float(av[i])
        if a < SPREAD * 3:
            i += 1; continue
        tp = e + tpk * a; sl = e - slk * a
        s, m, jo = float(cl[min(i+mh, n-1)]), "timeout", min(i+mh, n-1)
        for j in range(i+1, min(i+mh+1, n)):
            h, l = float(hi[j]), float(lo[j])
            btp, bsl = h >= tp, l <= sl
            if btp and bsl: s, m, jo = sl, "SL_amb", j; break
            if bsl: s, m, jo = sl, "SL", j; break
            if btp: s, m, jo = tp, "TP", j; break
            s, jo = float(cl[j]), j
        trs.append((tm[i], tm[jo], e, s, (s-e)-SPREAD, m, jo-i))
        conteo[k] = conteo.get(k, 0) + 1
        i = jo + 1
    if not trs:
        return None
    T = pd.DataFrame(trs, columns=["t_in", "t_out", "entry", "exit", "pnl", "motivo", "bars"])
    gp = T.loc[T.pnl > 0, "pnl"].sum(); gl = abs(T.loc[T.pnl <= 0, "pnl"].sum())
    eq = T.pnl.cumsum().values
    dd = float((np.maximum.accumulate(eq) - eq).max())
    return {"n": len(T), "win": float((T.pnl > 0).mean()), "pf": float(gp/(gl+1e-9)),
            "tot": float(T.pnl.sum()), "exp": float(T.pnl.mean()), "dd": dd,
            "score": float(T.pnl.sum() - 0.5*dd), "T": T}

def main():
    z = np.load(DATA / "opt_2025.npz", allow_pickle=True)
    hi, lo, cl, tm = z["hi"], z["lo"], z["cl"], z["t"]
    zv, pv, av, ses, ex = z["z"], z["p"], z["atr"], z["ses"], z["exp"]
    print(f"grid sobre n={len(cl)}...", flush=True)
    res = []
    for uz, pm, tpk, slk, mh, fe in itertools.product(
            [1.0, 1.5], [0.55, 0.60], [1.5, 2.0], [0.8, 1.0], [40, 60], [True, False]):
        r = correr(hi, lo, cl, tm, zv, pv, av, ses, ex, uz, pm, tpk, slk, mh, fe)
        if r:
            res.append((uz, pm, tpk, slk, mh, fe, r))
    res.sort(key=lambda x: x[6]["score"], reverse=True)
    rep = [f"combinaciones={len(res)}", "=== TOP 8 (solo LONG + sesion 7-20UTC + max3/dia) ==="]
    for uz, pm, tpk, slk, mh, fe, r in res[:8]:
        rep.append(f"uz={uz} pm={pm} TP={tpk} SL={slk} hold={mh} f_exp={fe} | "
                   f"n={r['n']} win={r['win']:.1%} PF={r['pf']:.2f} tot={r['tot']:+.1f} "
                   f"exp={r['exp']:+.2f} dd={r['dd']:.1f} score={r['score']:+.1f}")
    uz, pm, tpk, slk, mh, fe, r = res[0]
    T = r["T"]
    T.to_csv(DATA / "trades_opt.csv", index=False)
    T["eq"] = T["pnl"].cumsum()
    T[["t_out", "eq"]].to_csv(DATA / "equity_opt.csv", index=False)
    rep.append(f"MEJOR: uz={uz} pm={pm} TP={tpk} SL={slk} hold={mh} f_exp={fe}")
    rep.append(f"trades={r['n']} win={r['win']:.1%} PF={r['pf']:.2f} total={r['tot']:+.1f} dd={r['dd']:.1f} hold={T['bars'].mean():.1f}")
    mnt = T.groupby(pd.to_datetime(T["t_out"]).dt.tz_convert("UTC").dt.to_period("M"))["pnl"].agg(["sum", "count"])
    rep.append("--- MENSUAL ---")
    for per, rr in mnt.iterrows():
        rep.append(f"  {per}: {rr['sum']:+.1f} | {int(rr['count'])}")
    rep.append("MOTIVOS: " + str(T["motivo"].value_counts().to_dict()))
    rep.append("RIESGO VIVO: base 0.5%/trade; dd>100pts o 3 SL seguidas -> 0.25%; "
               "mes>+100pts -> 0.35%; max 3/dia; pausa dia si -2%; sesion 7-20 UTC.")
    txt = "\n".join(rep)
    print(txt, flush=True)
    (BASE / "reporte_opt_2025.txt").write_text(txt, encoding="utf-8")

if __name__ == "__main__":
    main()
