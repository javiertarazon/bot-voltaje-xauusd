"""Pipeline unificado de backtest."""
from pathlib import Path
import json
import sys

BASE = Path(__file__).parent


def main():
    config_path = BASE / "config.json"
    from config.validator import load_config
    cfg = load_config(str(config_path))

    from backtest.engine import BacktestEngine
    engine = BacktestEngine(cfg)

    simbolo = cfg.get("broker.symbol", "XAUUSD")
    periodo_inicio = cfg.get("backtest_params.periodo_inicio")
    periodo_fin = cfg.get("backtest_params.periodo_fin")

    print(f"Backtest {simbolo} {periodo_inicio} → {periodo_fin}", flush=True)
    resultado = engine.ejecutar(simbolo=simbolo, periodo_inicio=periodo_inicio, periodo_fin=periodo_fin)

    T = resultado.trades
    m = resultado.metricas

    # Guardar resultados
    data_dir = cfg.get("datos.directorio", "data")
    Path(data_dir).mkdir(exist_ok=True)
    if len(T) > 0:
        T.to_csv(Path(data_dir) / "trades_backtest.csv", index=False)
        T[["t_out", "eq"]].to_csv(Path(data_dir) / "equity_backtest.csv", index=False)

    # Guardar metricas
    reportes_dir = BASE / "reportes"
    reportes_dir.mkdir(exist_ok=True)
    reporte = [
        f"=== BACKTEST UNIFICADO {simbolo} ===",
        f"período: {periodo_inicio} → {periodo_fin}",
        f"trades={m['n']} winrate={m['winrate']:.1%} PF={m['pf']:.2f}",
        f"expectancy={m['exp']:+.3f} total={m['total']:+.1f}",
        f"max_dd={m['dd']:.1f} sharpe={m['sharpe']:.2f}",
        f"avg_win={m.get('avg_win', 0):+.2f} avg_loss={m.get('avg_loss', 0):+.2f}",
        f"max_racha_gan={m.get('max_racha_ganancia', 0)} max_racha_perd={m.get('max_racha_perdida', 0)}",
    ]
    if len(T) > 0 and "mes" in T.columns:
        reporte.append("--- MENSUAL ---")
        for mes, rr in T.groupby(T["t_out"].dt.to_period("M").astype(str))["pnl"].agg(["sum", "count"]).iterrows():
            reporte.append(f"  {mes}: {rr['sum']:+.1f} | n={int(rr['count'])}")

    txt = "\n".join(reporte)
    print(txt, flush=True)
    (reportes_dir / "reporte_backtest_unificado.txt").write_text(txt, encoding="utf-8")
    print(f"\nArchivos: {data_dir}/trades_backtest.csv, {data_dir}/equity_backtest.csv, {reportes_dir}/reporte_backtest_unificado.txt", flush=True)


if __name__ == "__main__":
    main()
