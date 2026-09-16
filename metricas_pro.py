"""Metricas profesionales + grafica equity/DD de la optimizacion 2025.
Uso: py metricas_pro.py
Lee data/trades_opt.csv -> reporte_metricas_pro.txt + equity_dd_2025.png
Sin MT5 (offline). Requiere matplotlib.
"""
from pathlib import Path
import numpy as np
import pandas as pd
BASE = Path(__file__).parent
DATA = BASE / "data"

def main():
    t = pd.read_csv(DATA / "trades_opt.csv")
    t["t_out"] = pd.to_datetime(t["t_out"], utc=True)
    t = t.sort_values("t_out").reset_index(drop=True)
    r = t["pnl"].values.astype(float)
    n = len(r)
    wins = (r > 0).sum()
    winr = wins / n
    gp = r[r > 0].sum()
    gl = abs(r[r <= 0].sum())
    pf = gp / (gl + 1e-9)
    exp = r.mean()
    tot = r.sum()
    eq = np.cumsum(r)
    peak = np.maximum.accumulate(eq)
    dd = peak - eq
    maxdd = dd.max()
    # Sharpe / Sortino por trade (anualizado por trades)
    sharpe = float(r.mean() / (r.std(ddof=1) + 1e-9) * np.sqrt(n))
    dn = r[r < 0]
    sortino = float(r.mean() / (dn.std(ddof=1) + 1e-9) * np.sqrt(n)) if len(dn) > 1 else 0.0
    # Calmar = total / maxdd
    calmar = float(tot / (maxdd + 1e-9))
    # Mejor/peor trade, avg win/loss, payoff
    avgw = float(r[r > 0].mean())
    avgl = float(r[r <= 0].mean())
    payoff = float(avgw / (abs(avgl) + 1e-9))
    best = float(r.max())
    worst = float(r.min())
    # Rachas
    w = (r > 0).astype(int)
    maxrw = maxrl = curw = curl = 0
    for x in w:
        if x:
            curw += 1; maxrw = max(maxrw, curw); curl = 0
        else:
            curl += 1; maxrl = max(maxrl, curl); curw = 0
    # Mensual
    t["mes"] = t["t_out"].dt.to_period("M").astype(str)
    m = t.groupby("mes")["pnl"].agg(["sum", "count", "mean"])
    m["win"] = t.groupby("mes").apply(lambda x: (x["pnl"] > 0).mean(), include_groups=False)
    meses_pos = int((m["sum"] > 0).sum())
    # Ulcer index (profundidad/duracion DD)
    ulcer = float(np.sqrt((dd ** 2).mean()))
    # Tiempo en DD: % trades bajo peak
    pct_dd = float((dd > 0).mean() * 100)
    # Punto de recuperacion maximo (barras)
    rec = 0
    j = int(np.argmax(dd))
    if dd[j] > 0:
        pk = peak[j]
        k = j + 1
        while k < n and eq[k] < pk:
            k += 1
        rec = k - j
    lot = 0.01
    usd = tot * 1.0
    rep = []
    rep.append("=== METRICAS PROFESIONALES 2025 FluxoV2 LONG (M15 XAUUSD) ===")
    rep.append(f"trades={n} periodo={t['t_out'].iloc[0].date()} -> {t['t_out'].iloc[-1].date()}")
    rep.append(f"WINRATE={winr:.2%} ({wins}/{n}) PROFIT_FACTOR={pf:.2f} EXPECTANCY={exp:+.3f} pts")
    rep.append(f"TOTAL={tot:+.1f} pts (~{usd:+.0f} USD @0.01) AVG_WIN={avgw:+.2f} AVG_LOSS={avgl:+.2f} PAYOFF={payoff:.2f}")
    rep.append(f"MAX_DRAWDOWN={maxdd:.1f} pts CALMAR={calmar:.2f} ULCER={ulcer:.2f} TIEMPO_EN_DD={pct_dd:.1f}% REC_MAX={rec} trades")
    rep.append(f"SHARPE*={sharpe:+.2f} SORTINO*={sortino:+.2f} (*anualizado por trades, rf=0)")
    rep.append(f"BEST={best:+.2f} WORST={worst:+.2f} RACHA_W={maxrw} RACHA_L={maxrl}")
    rep.append(f"MESES_POS={meses_pos}/{len(m)} HOLD_MEDIO={t['bars'].mean():.1f} velas")
    rep.append("--- MENSUAL ---")
    for mes, rr in m.iterrows():
        rep.append(f"  {mes}: {rr['sum']:+.1f} pts | n={int(rr['count'])} | win={(rr['win']):.0%} | exp={rr['mean']:+.2f}")
    rep.append("NOTA: spread 0.16 incluido, sin comision/swap/slippage. 0.01 lote ~= 1 USD/pt.")
    txt = "\n".join(rep)
    print(txt, flush=True)
    (BASE / "reporte_metricas_pro.txt").write_text(txt, encoding="utf-8")
    # --- grafica ---
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True,
                                   gridspec_kw={"height_ratios": [3, 1.5]})
    tt = t["t_out"]
    ax1.plot(tt, eq, lw=1.5, label="Equity pts")
    ax1.plot(tt, peak, lw=1.0, ls="--", label="Peak")
    ax1.fill_between(tt, eq, peak, alpha=0.25, label="Drawdown zona")
    ax1.set_title("XAUUSD M15 2025 FluxoV2 LONG - Equity (+461.2 pts, PF 1.29)")
    ax1.set_ylabel("pts acumulados")
    ax1.legend(loc="upper left")
    ax1.grid(alpha=0.3)
    ax2.fill_between(tt, -dd, 0, alpha=0.6, label="Drawdown pts")
    ax2.set_ylabel("DD pts")
    ax2.set_xlabel("2025")
    ax2.legend(loc="lower left")
    ax2.grid(alpha=0.3)
    ax2.xaxis.set_major_locator(mdates.MonthLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    fig.tight_layout()
    out = BASE / "equity_dd_2025.png"
    fig.savefig(out, dpi=110)
    print(f"grafica -> {out}", flush=True)

if __name__ == "__main__":
    main()
