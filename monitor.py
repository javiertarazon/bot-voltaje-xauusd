"""Monitor de rendimiento vivo: lee trading_log.db y da metricas + accion de riesgo.
Uso: py monitor.py   -> reporte_monitor.txt
"""
import sqlite3
from pathlib import Path
import pandas as pd
BASE = Path(__file__).parent
DB = BASE / "trading_log.db"
c = sqlite3.connect(DB)
T = pd.read_sql("SELECT * FROM demo_trades WHERE cierre!='abierta' AND pnl IS NOT NULL", c)
N = pd.read_sql("SELECT razon, COUNT(*) n FROM no_trades GROUP BY razon ORDER BY n DESC LIMIT 10", c)
E = pd.read_sql("SELECT ts, balance, equity, riesgo_pct FROM equity ORDER BY id", c)
c.close()
L = []
L.append(f"=== MONITOR FLUXOV2 LIVE DEMO {pd.Timestamp.now(tz='UTC')} ===")
L.append(f"trades cerrados={len(T)} no_trades registradas={int(N['n'].sum())} samples equity={len(E)}")
if len(T) == 0:
    L.append("sin trades cerrados todavia. El bot sigue supervisando.")
else:
    r = T["pnl"].astype(float).values
    w = float((r > 0).mean()); gp = r[r > 0].sum(); gl = abs(r[r <= 0].sum())
    pf = float(gp / (gl + 1e-9)); exp = float(r.mean())
    eq = CAP0 = 10000.0 + r.cumsum()
    pk = eq.cummax(); dd = (pk - eq) / pk * 100
    L.append(f"WINRATE={w:.1%} PF={pf:.2f} exp=${exp:+.2f} total=${r.sum():+.2f} maxDD={dd.max():.2f}%")
    L.append(f"motivos cierre: {T['cierre'].value_counts().to_dict()}")
    L.append(f"riesgo_pct usado: {T['riesgo_pct'].unique().tolist()}")
    L.append(f"z medio entrada={T['z'].mean():.2f} p_up medio={T['p_up'].mean():.3f} mc medio={T['p_mc'].mean():.3f}")
    L.append("--- ultimos 10 trades ---")
    for _, t in T.tail(10).iterrows():
        L.append(f"  {t['ts'][:16]} lote={t['lote']} pnl=${t['pnl']:.2f} cierre={t['cierre']} z={t['z']:.2f}")
    L.append("--- ACCION DE RIESGO (mi decision como gestor) ---")
    if pf < 1.0 and len(r) >= 15:
        L.append("PF vivo < 1.0 con n>=15: REDUCIR riesgo a 0.25% y pausar 24h si ademas DD>5%.")
    elif dd.max() > 10:
        L.append("DD vivo > 10%: riesgo a 0.25% hasta recuperar peak.")
    elif w < 0.25 and len(r) >= 20:
        L.append("REVISAR: winrate <25% con n>=20 (el backtest decia 34%).")
    else:
        L.append("Metricas dentro de lo esperado del backtest (win~34%, PF~1.2). Mantener 0.5%.")
L.append("--- top no_trades (por que NO opera) ---")
for _, x in N.iterrows():
    L.append(f"  {x['n']:4d}  {x['razon']}")
open(BASE / "reporte_monitor.txt", "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L), flush=True)