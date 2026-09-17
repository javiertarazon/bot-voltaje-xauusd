"""Detección automática de debilidades en resultados de backtest."""
import numpy as np
import pandas as pd


def detectar_racias_sl_consecutivas(trades: pd.DataFrame, n: int = 3) -> dict:
    """Detecta N+ SL consecutivos."""
    if len(trades) == 0:
        return {"sl_consecutivas": [], "count": 0}
    r = trades["pnl"].values
    consecutivas = []
    cur = 0
    for i, x in enumerate(r):
        if x <= 0:
            cur += 1
            if cur >= n:
                consecutivas.append(i)
        else:
            cur = 0
    return {"sl_consecutivas": consecutivas, "count": len(consecutivas)}


def detectar_degradacion_winrate(trades: pd.DataFrame, ventana: int = 20) -> dict:
    """Winrate decreciente en ventanas móviles."""
    if len(trades) < ventana * 2:
        return {"degradada": False, "ratio": 0.0}
    wr = (trades["pnl"] > 0).astype(float)
    scores = wr.rolling(ventana).mean()
    primera = scores.dropna().iloc[0]
    ultima = scores.dropna().iloc[-1]
    ratio = (primera - ultima) / primera if primera > 0 else 0.0
    return {"degradada": ratio > 0.3, "ratio": ratio, "primera": primera, "ultima": ultima}


def comparar_por_regimen(trades: pd.DataFrame, regime_col: str = "regimen") -> dict:
    """Compara PF y WR por régimen."""
    if regime_col not in trades.columns:
        return {"sin_datos": True}
    result = {}
    for name, grp in trades.groupby(regime_col):
        gp = grp.loc[grp["pnl"] > 0, "pnl"].sum()
        gl = abs(grp.loc[grp["pnl"] <= 0, "pnl"].sum())
        pf = gp / (gl + 1e-9) if gl > 0 else float("inf")
        wr = (grp["pnl"] > 0).mean()
        result[str(name)] = {"n": len(grp), "pf": pf, "winrate": wr, "total": grp["pnl"].sum()}
    return {"por_regimen": result}


def analizar_horas(trades: pd.DataFrame) -> dict:
    """Qué horas UTC tienen mejor/peor expectancy."""
    if "t_in" not in trades.columns:
        return {}
    t = trades.copy()
    t["hora"] = pd.to_datetime(t["t_in"]).dt.hour
    res = t.groupby("hora")["pnl"].agg(["count", "sum", "mean"])
    res.columns = ["n", "total", "exp"]
    return res.to_dict("index")


def analizar_tamano_posicion(trades: pd.DataFrame, size_col: str = "size") -> dict:
    """Afecta el tamaño al resultado?"""
    if size_col not in trades.columns:
        return {"sin_datos": True}
    return trades.groupby(size_col)["pnl"].agg(["count", "mean", "sum"]).to_dict("index")


def detectar_overfit(trades: pd.DataFrame, ventana: int = 50) -> dict:
    """Sharpe decreciente sobre ventanas = sobreoptimización."""
    if len(trades) < ventana * 2:
        return {"sobreoptimizado": False, "ratio": 0.0}
    pnl = trades["pnl"].values
    scores = []
    for i in range(ventana, len(pnl), ventana // 2):
        slice_p = pnl[max(0, i - ventana):i]
        if len(slice_p) >= 5:
            sh = slice_p.mean() / (slice_p.std(ddof=1) + 1e-9) * np.sqrt(len(slice_p))
            scores.append(sh)
    if len(scores) < 2:
        return {"sobreoptimizado": False, "ratio": 0.0}
    ratio = (scores[0] - scores[-1]) / abs(scores[0]) if scores[0] != 0 else 0.0
    return {"sobreoptimizado": ratio > 0.5, "ratio": ratio, "scores": scores}


def score_debilidades(trades: pd.DataFrame) -> dict:
    """Score 0-100 de problemas encontrados."""
    problemas = []
    puntuacion = 0

    sl = detectar_racias_sl_consecutivas(trades, 3)
    if sl["count"] > 0:
        problemas.append(f"{sl['count']} rachas de 3+ SL consecutivas")
        puntuacion += min(30, sl['count'] * 10)

    deg = detectar_degradacion_winrate(trades)
    if deg["degradada"]:
        problemas.append(f"Winrate degradada: {deg['primera']:.0%} → {deg['ultima']:.0%}")
        puntuacion += 20

    over = detectar_overfit(trades)
    if over["sobreoptimizado"]:
        problemas.append(f"Posible sobreoptimización (ratio={over['ratio']:.0%})")
        puntuacion += 25

    horas = analizar_horas(trades)
    if horas:
        peor_hora = min(horas.items(), key=lambda x: x[1].get("exp", x[1].get("mean", 0)))
        if peor_hora[1].get("exp", peor_hora[1].get("mean", 0)) < -1.0:
            problemas.append(f"Hora {peor_hora[0]}UTC: exp={peor_hora[1].get('exp', peor_hora[1].get('mean', 0)):+.2f}")
            puntuacion += 10

    return {
        "score": min(100, puntuacion),
        "problemas": problemas,
        "rachas_sl": sl,
        "degradacion_wr": deg,
        "overfit": over,
        "horas": horas,
    }
