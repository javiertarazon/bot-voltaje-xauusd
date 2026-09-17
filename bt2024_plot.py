"""Grafica equity USD + DD% 2024. Uso: py bt2024_plot.py [M15|M5]"""
import sys
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
BASE = Path(__file__).parent
DATA = BASE / "data"
TF = (sys.argv[1] if len(sys.argv) > 1 else "M15").upper()
CAP0 = 1000.0
T = pd.read_csv(DATA / f"trades_2024_{TF}.csv")
T["t_out"] = pd.to_datetime(T["t_out"], utc=True)
T = T.sort_values("t_out").reset_index(drop=True)
T["eq"] = CAP0 + T["neto"].cumsum()
pk = T["eq"].cummax()
ddp = (pk - T["eq"]) / pk * 100
fig, (a1, a2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1.5]})
tt = T["t_out"]
a1.plot(tt, T["eq"], lw=1.5, label="Balance USD")
a1.axhline(CAP0, ls="--", lw=1.0, label="Capital inicial 1000 USD")
a1.fill_between(tt, T["eq"], pk, alpha=0.25)
a1.set_title(f"XAUUSD 2024 {TF} FluxoV2 - 1000 USD -> {T['eq'].iloc[-1]:,.2f} ({(T['eq'].iloc[-1]-CAP0)/CAP0*100:+.1f}%) DD {ddp.max():.1f}%")
a1.set_ylabel("USD")
a1.legend(loc="upper left")
a1.grid(alpha=0.3)
a2.fill_between(tt, -ddp, 0, alpha=0.6)
a2.set_ylabel("DD %")
a2.set_xlabel("2024")
a2.grid(alpha=0.3)
a2.xaxis.set_major_locator(mdates.MonthLocator())
a2.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
fig.tight_layout()
out = BASE / f"equity_2024_{TF}.png"
fig.savefig(out, dpi=110)
print(f"OK -> {out} final=${T['eq'].iloc[-1]:,.2f} ddmax={ddp.max():.2f}%", flush=True)
