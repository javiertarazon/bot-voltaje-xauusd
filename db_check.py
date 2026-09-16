import sqlite3
DB = r"D:\proyectos_javier\proyectos\xauusd-trader\trading_log.db"
c = sqlite3.connect(DB)
out = []
for t in ["equity", "no_trades", "demo_trades", "paper_trades"]:
    try:
        n = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        out.append(f"{t}={n}")
    except Exception as e:
        out.append(f"{t}=ERR {e}")
r = c.execute("SELECT ts,balance,equity,riesgo_pct FROM equity ORDER BY id DESC LIMIT 2").fetchall()
out.append(f"equity_ultimas={r}")
r = c.execute("SELECT ts,razon FROM no_trades ORDER BY id DESC LIMIT 2").fetchall()
out.append(f"no_trades_ultimas={r}")
r = c.execute("SELECT ts,ticket,lote,pnl,cierre,motivo FROM demo_trades ORDER BY id DESC LIMIT 5").fetchall()
out.append(f"demo_trades_ultimas={r}")
r = c.execute("SELECT MAX(balance) FROM equity").fetchone()[0]
out.append(f"max_bal_visto={r}")
c.close()
open(r"D:\proyectos_javier\proyectos\xauusd-trader\cert_db.txt", "w").write("\n".join(out) + "\n")