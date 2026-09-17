"""Generador de reportes markdown."""
from pathlib import Path
import numpy as np


def generar_reporte_completo(resultado, debilidades: dict = None) -> str:
    """Genera reporte markdown completo."""
    T = resultado.trades
    m = resultado.metricas

    rep = []
    rep.append("=== REPORTE DE BACKTEST UNIFICADO ===")
    rep.append(f"trades={m['n']} winrate={m['winrate']:.1%} PF={m['pf']:.2f}")
    rep.append(f"expectancy={m['exp']:+.3f} total={m['total']:+.1f}")
    rep.append(f"max_drawdown={m['dd']:.1f} sharpe={m['sharpe']:.2f}")
    rep.append(f"calmar={m['calmar']:.2f} sortino={m['sortino']:.2f}")
    rep.append(f"avg_win={m.get('avg_win', 0):+.2f} avg_loss={m.get('avg_loss', 0):+.2f} payoff={m.get('payoff', 0):.2f}")
    rep.append(f"max_racha_gan={m.get('max_racha_ganancia', 0)} max_racha_perd={m.get('max_racha_perdida', 0)}")

    if len(T) > 0 and "t_out" in T.columns:
        T2 = T.copy()
        T2["mes"] = T2["t_out"].dt.strftime("%Y-%m")
        rep.append("--- MENSUAL ---")
        for mes, gg in T2.groupby("mes")["pnl"].agg(["sum", "count", "mean"]).iterrows():
            rep.append(f"  {mes}: {gg['sum']:+.1f} pts | n={int(gg['count'])} | exp={gg['mean']:+.2f}")

    rep.append("--- DEBILIDADES ---")
    if debilidades:
        rep.append(f"Score debilidad: {debilidades.get('score', 0)}/100")
        for p in debilidades.get("problemas", []):
            rep.append(f"  - {p}")
    else:
        rep.append("No calculado")

    rep.append("--- CONFIGURACIÓN ---")
    cfg = resultado.config
    for k in ["broker.symbol", "estrategia.uz", "estrategia.pm", "riesgo.base_pct"]:
        v = cfg.get(k) if isinstance(cfg, dict) else None
        if v is not None:
            rep.append(f"  {k}: {v}")

    txt = "\n".join(rep)

    reportes_dir = Path(__file__).parent.parent / "reportes"
    reportes_dir.mkdir(exist_ok=True)
    (reportes_dir / "reporte_completo.md").write_text(txt, encoding="utf-8")

    return txt
