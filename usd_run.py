"""Backtest USD parte B: capital 1000 + riesgo + costes. Uso: py usd_run.py"""
from pathlib import Path
import datetime as dtm
import numpy as np
import pandas as pd
BASE = Path(__file__).parent
DATA = BASE / "data"
CAP0, RISK = 1000.0, 0.005
SPREAD_PX, SLIP_PX = 0.16, 0.05
SWAP_L = -45.0
USD_PT_LOTE = 100.0
UZ, PM, TPK, SLK, MH = 1.0, 0.55, 2.0, 0.8, 60
def main():
    z = np.load(DATA / "usd_2025.npz", allow_pickle=True)
    hi, lo, cl, tm = z["hi"], z["lo"], z["cl"], z["t"]
    zv, pv, av, hh = z["z"], z["p"], z["atr"], z["h"]
    tmi = pd.to_datetime(tm, utc=True)
    n = len(cl)
    bal, peak, maxdd = CAP0, CAP0, 0.0
    trs, eq = [], []
    conteo = {}
    i = 120
    while i < n - 2:
        h = int(hh[i])
        if h < 7 or h > 20:
            i += 1; continue
        key = str(tmi[i].date())
        if conteo.get(key, 0) >= 3:
            i += 1; continue
        if not (zv[i] > UZ and pv[i] > PM):
            i += 1; continue
        a = float(av[i])
        if a < SPREAD_PX * 3:
            i += 1; continue
        sl_d = SLK * a
        lote = max(0.01, round((bal * RISK) / (sl_d * USD_PT_LOTE + 1e-9) / 0.01) * 0.01)
        lote = min(lote, 10.0)
        e = float(cl[i]) + SLIP_PX
        tp, sl = e + TPK * a, e - sl_d
        s, m, jo = float(cl[min(i+MH, n-1)]), "timeout", min(i+MH, n-1)
        for j in range(i+1, min(i+MH+1, n)):
            btp, bsl = float(hi[j]) >= tp, float(lo[j]) <= sl
            if btp and bsl: s, m, jo = sl, "SL_amb", j; break
            if bsl: s, m, jo = sl, "SL", j; break
            if btp: s, m, jo = tp, "TP", j; break
            s, jo = float(cl[j]), j
        s = s - SLIP_PX
        bruto = (s - e) * USD_PT_LOTE * lote - SPREAD_PX * USD_PT_LOTE * lote
        di, do = tmi[i].date(), tmi[jo].date()
        swap = 0.0
        dd = di
        while dd < do:
            swap += SWAP_L * lote * (3 if dd.weekday() == 2 else 1)
            dd += dtm.timedelta(days=1)
        neto = bruto + swap
        bal += neto
        peak = max(peak, bal)
        maxdd = max(maxdd, peak - bal)
        trs.append((tmi[i], tmi[jo], lote, e, s, bruto, swap, neto, bal, m))
        eq.append((tmi[jo], bal))
        conteo[key] = conteo.get(key, 0) + 1
        i = jo + 1
        if bal <= CAP0 * 0.5:
            break
    T = pd.DataFrame(trs, columns=["t_in", "t_out", "lote", "entry", "exit", "bruto", "swap", "neto", "bal", "motivo"])
    T.to_csv(DATA / "trades_usd.csv", index=False)
    pd.DataFrame(eq, columns=["t", "bal"]).to_csv(DATA / "equity_usd.csv", index=False)
    r = T["neto"].values
    nn = len(T)
    w = float((r > 0).mean())
    gp = r[r > 0].sum(); gl = abs(r[r <= 0].sum())
    pf = float(gp / (gl + 1e-9))
    retp = (bal - CAP0) / CAP0 * 100
    ddp = maxdd / peak * 100
    sh = float(r.mean() / (r.std(ddof=1) + 1e-9) * (nn ** 0.5))
    T["mes"] = pd.to_datetime(T["t_out"], utc=True).dt.strftime("%Y-%m")
    rep = [f"=== BACKTEST USD 2025 capital ${CAP0:.0f} riesgo 0.5% ===",
           "Costes: spread 16 + slippage 5x2 + swap LONG -45/lote/noche x3 mie.",
           f"trades={nn} win={w:.1%} PF={pf:.2f} exp=${r.mean():+.2f}",
           f"FINAL=${bal:,.2f} TOTAL=${r.sum():+,.2f} ({retp:+.2f}%) MAXDD=${maxdd:,.2f} ({ddp:.2f}%) SHARPE*={sh:+.2f}",
           f"lote medio={T['lote'].mean():.3f} max={T['lote'].max():.2f} swap=${T['swap'].sum():+.2f}",
           "--- MENSUAL USD ---"]
    for mes, gg in T.groupby("mes")["neto"].agg(["sum", "count", "mean"]).iterrows():
        rep.append(f"  {mes}: ${gg['sum']:+.2f} ({gg['sum']/CAP0*100:+.2f}%) n={int(gg['count'])} exp=${gg['mean']:+.2f}")
    txt = "\n".join(rep)
    print(txt, flush=True)
    (BASE / "reporte_backtest_usd.txt").write_text(txt, encoding="utf-8")
if __name__ == "__main__":
    main()
