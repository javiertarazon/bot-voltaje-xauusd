"""Grafica equity/DD 2025 (solo plot). Uso: py plot_equity.py"""
from pathlib import Path
import pandas as pd
BASE = Path(__file__).parent
DATA = BASE / "data"
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
t = pd.read_csv(DATA / "trades_opt.csv")
t["t_out"] = pd.to_datetime(t["t_out"], utc=True)
t = t.sort_values("t_out").reset_index(drop=True)
t["eq"] = t["pnl"].cumsum()
pk = t["eq"].cummax()
dd = pk - t["eq"]
fig, (a1, a2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1.5]})
tt = t["t_out"]
a1.plot(tt, t["eq"], lw=1.5, label="Equity pts")
a1.plot(tt, pk, lw=1.0, ls="--", label="Peak")
a1.fill_between(tt, t["eq"], pk, alpha=0.25)
a1.set_title("XAUUSD M15 2025 FluxoV2 LONG - Equity +461.2 pts PF 1.29 DD 85.4")
a1.set_ylabel("pts")
a1.legend(loc="upper left")
a1.grid(alpha=0.3)
a2.fill_between(tt, -dd, 0, alpha=0.6)
a2.set_ylabel("DD pts")
a2.set_xlabel("2025")
a2.grid(alpha=0.3)
a2.xaxis.set_major_locator(mdates.MonthLocator())
a2.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
fig.tight_layout()
out = BASE / "equity_dd_2025.png"
fig.savefig(out, dpi=110)
print(f"OK grafica -> {out} trades={len(t)} total={t['pnl'].sum():+.1f} dd={dd.max():.1f}", flush=True)
