"""Validación temporal sin solapamiento entre períodos.

Ejecuta la configuración fija sobre años consecutivos y marca la estrategia
como no apta si la ventaja desaparece fuera de muestra.
"""
from pathlib import Path
import json
import pandas as pd

BASE = Path(__file__).resolve().parent

def main():
    from config.validator import load_config
    from backtest.engine import BacktestEngine
    cfg = load_config(str(BASE / "config.json"))
    engine = BacktestEngine(cfg)
    rows = []
    for year in range(2023, 2026):
        result = engine.ejecutar(
            simbolo=cfg.get("broker.symbol", "XAUUSD"),
            periodo_inicio=f"{year}-01-01",
            periodo_fin=f"{year + 1}-01-01",
        )
        m = result.metricas
        rows.append({"year": year, "trades": m["n"], "pf": m["pf"],
                     "expectancy": m["exp"], "total": m["total"], "dd": m["dd"]})
    report = pd.DataFrame(rows)
    report["aceptable"] = (report["trades"] >= 30) & (report["pf"] >= 1.05) & (report["expectancy"] > 0)
    robusta = bool(report["aceptable"].all())
    print(report.to_string(index=False))
    print(f"\nROBUSTA={robusta}; criterio: cada año PF>=1.05, expectancy>0 y >=30 trades")
    out = BASE / "reportes" / "walkforward_2023_2025.csv"
    out.parent.mkdir(exist_ok=True)
    report.to_csv(out, index=False)
    (BASE / "reportes" / "walkforward_2023_2025.json").write_text(
        json.dumps({"robusta": robusta, "rows": rows}, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
