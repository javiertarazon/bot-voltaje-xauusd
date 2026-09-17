"""Detección de régimen de mercado y adaptación automática."""
from typing import Optional
import numpy as np
import pandas as pd


def detectar_regimen(
    historico: pd.DataFrame,
    ventana: int = 60,
) -> str:
    """Detecta régimen actual de XAUUSD.

    Criterios:
    - Alcista: precio > MA50 Y ATR14 > ATR100 AND días consecutivos up >= 3
    - Bajista: precio < MA50 AND ATR14 > ATR100 AND días consecutivos down >= 3
    - Lateral: ninguno de los anteriores

    Retorna: "alcista" | "bajista" | "lateral"
    """
    if len(historico) < ventana:
        return "lateral"

    close = historico["close"].values[-ventana:]
    px = close[-1]

    ma50 = pd.Series(close).rolling(50).mean().iloc[-1]

    if "atr" in historico.columns:
        atr14 = historico["atr"].iloc[-1]
        atr100 = historico["atr"].iloc[-100] if len(historico) >= 100 else historico["atr"].mean()
    else:
        tr = pd.concat([
            historico["high"] - historico["low"],
            (historico["high"] - historico["close"].shift(1)).abs(),
            (historico["low"] - historico["close"].shift(1)).abs(),
        ], axis=1).max(axis=1)
        atr14 = tr.rolling(14).mean().iloc[-1]
        atr100 = tr.rolling(100).mean().iloc[-1]

    if atr14 <= 0 or atr100 <= 0:
        return "lateral"

    cambio = pd.Series(close).pct_change().fillna(0).values[-5:]
    consecutivo_up = 0
    consecutivo_down = 0
    for c in cambio[::-1]:
        if c > 0:
            consecutivo_up += 1
            consecutivo_down = 0
        elif c < 0:
            consecutivo_down += 1
            consecutivo_up = 0
        else:
            break

    dias_previos_up = bool(historico.get("up_prev", pd.Series([False]*len(historico))).iloc[-1]) if "up_prev" in historico.columns else True

    if px > ma50 and atr14 > atr100 and consecutivo_up >= 3:
        return "alcista"
    elif px < ma50 and atr14 > atr100 and consecutivo_down >= 3:
        return "bajista"
    return "lateral"


def obtener_parametros_por_regimen(
    regimen: str,
    config: "Config",
) -> dict:
    """Devuelve uz, pm, tp_k, sl_k según el régimen."""
    if regimen == "alcista":
        return config.get(
            "regimen.params_mercado_alcista",
            {"uz": 1.0, "pm": 0.55, "tp_k": 2.0, "sl_k": 0.8},
        )
    elif regimen == "bajista":
        return config.get(
            "regimen.params_mercado_bajista",
            {"uz": 1.2, "pm": 0.60, "tp_k": 1.8, "sl_k": 0.7},
        )
    else:
        return config.get(
            "regimen.params_mercado_lateral",
            {"uz": 1.0, "pm": 0.55, "tp_k": 2.0, "sl_k": 0.8},
        )


def estimar_hora_pico(
    historico: pd.DataFrame,
    columna_pnl: Optional[str] = None,
) -> dict:
    """Analiza qué horas UTC tienen mejor expectancy.

    Usa columna de pnl si existe, o intenta estimar por velocidad de precio.
    """
    if "time" not in historico.columns:
        return {}
    df = historico.copy()
    df["hora"] = df["time"].dt.hour
    if columna_pnl and columna_pnl in df.columns:
        horas = df.groupby("hora")[columna_pnl].agg(["count", "sum", "mean"])
        horas["exp"] = horas["sum"] / horas["count"]
        return horas.to_dict("index")
    return {}
